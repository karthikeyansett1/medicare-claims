"""Fail-closed PostgreSQL AST policy, independently enforced before every query."""
from pathlib import Path
import sqlglot
from sqlglot import exp
from sqlglot.optimizer.qualify import qualify
from sqlglot.optimizer.scope import traverse_scope
import yaml

TABLES = yaml.safe_load((Path(__file__).parent / 'semantic_layer.yaml').read_text())['tables']
SCHEMA = {}
for name, meta in TABLES.items():
    schema, table = name.split('.')
    SCHEMA.setdefault(schema, {})[table] = {c: ('TEXT' if v['type'] == 'ARRAY' else v['type']) for c, v in meta['columns'].items()}
FUNCTIONS = {'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'COALESCE', 'NULLIF', 'ROUND',
             'AND', 'OR', 'ABS', 'ROW_NUMBER', 'RANK', 'DENSE_RANK', 'NTILE', 'LAG', 'LEAD',
             'CAST', 'EXTRACT', 'DATE_TRUNC', 'LOWER', 'UPPER', 'CASE', 'IF'}
CASTS = {'INT', 'BIGINT', 'SMALLINT', 'DECIMAL', 'DOUBLE', 'FLOAT', 'TEXT', 'VARCHAR', 'BOOLEAN', 'DATE', 'TIMESTAMP'}

class GuardrailError(ValueError):
    pass


def validate_sql(sql: str) -> str:
    if not isinstance(sql, str) or not sql.strip() or len(sql) > 20000:
        raise GuardrailError('SQL must be nonempty and at most 20000 characters.')
    try:
        statements = sqlglot.parse(sql, read='postgres')
    except sqlglot.errors.SqlglotError as e:
        raise GuardrailError('SQL cannot be parsed as PostgreSQL.') from e
    if len(statements) != 1 or not isinstance(statements[0], exp.Select):
        raise GuardrailError('Exactly one SELECT is allowed (SELECT CTEs are supported).')
    tree = statements[0]
    forbidden = ('Insert', 'Update', 'Delete', 'Merge', 'Create', 'Drop', 'Alter', 'Command',
                 'Copy', 'Into', 'Lock', 'Transaction', 'Set', 'Union', 'Intersect', 'Except',
                 'DPipe', 'Operator', 'Lateral', 'Unnest', 'TableSample', 'Parameter', 'Placeholder', 'SessionParameter')
    if any(type(n).__name__ in forbidden for n in tree.walk()):
        raise GuardrailError('Only ordinary read-only SELECT expressions are allowed.')
    for node in tree.find_all(exp.With):
        if node.args.get('recursive'):
            raise GuardrailError('Recursive CTEs are not allowed.')
    for node in tree.find_all(exp.CTE):
        if not isinstance(node.this, exp.Select):
            raise GuardrailError('CTEs must contain SELECT only.')
    for node in tree.find_all(exp.Func):
        name = node.name.upper() if isinstance(node, exp.Anonymous) else node.sql_name()
        if name not in FUNCTIONS or isinstance(node.parent, exp.Dot):
            raise GuardrailError('Function is outside the analytics allowlist.')
    for node in tree.find_all(exp.Cast):
        if getattr(node.to.this, 'value', None) not in CASTS or node.to.args.get('kind'):
            raise GuardrailError('Only built-in scalar analytics casts are allowed.')
    physical = 0
    try:
        for scope in traverse_scope(tree):
            for _, source in scope.selected_sources.values():
                if isinstance(source, exp.Table):
                    if not isinstance(source.this, exp.Identifier) or source.catalog:
                        raise GuardrailError('Table functions and catalog references are forbidden.')
                    if f'{source.db}.{source.name}' not in TABLES:
                        raise GuardrailError('Use an explicitly schema-qualified approved table.')
                    physical += 1
            for join in scope.expression.args.get('joins', []):
                if not (join.args.get('on') or join.args.get('using')) or join.args.get('method'):
                    raise GuardrailError('Joins require explicit ON or USING keys; no natural/cross joins.')
        if not physical:
            raise GuardrailError('Query must read an approved analytics table.')
        # Resolves CTE/derived aliases and rejects nonexistent or ambiguous columns.
        qualify(tree.copy(), dialect='postgres', schema=SCHEMA, validate_qualify_columns=True)
    except GuardrailError:
        raise
    except (sqlglot.errors.SqlglotError, ValueError) as e:
        raise GuardrailError('Unknown, ambiguous or unqualified column/table reference.') from e
    limit = tree.args.get('limit')
    if limit:
        value = limit.expression
        if not isinstance(value, exp.Literal) or not value.is_int or int(value.this) < 0:
            raise GuardrailError('LIMIT must be a nonnegative integer constant.')
        cap = min(500, int(value.this))
    else:
        cap = 500
    tree.limit(cap, copy=False)
    return tree.sql(dialect='postgres')
