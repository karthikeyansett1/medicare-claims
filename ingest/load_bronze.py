"""Verified, transactional COPY load of the profiled source files into bronze.

No cleaning or source type conversion occurs. All five project tables are
replaced as one transaction; reruns do not append duplicate rows.
"""
import argparse
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import time

from dotenv import load_dotenv
from psycopg import sql

from ingest.db import get_conn
from ingest.download import ROOT, read_manifest, verify_record

TABLES = {'beneficiary_2008': 'beneficiary', 'beneficiary_2009': 'beneficiary',
          'beneficiary_2010': 'beneficiary', 'inpatient': 'inpatient',
          'outpatient': 'outpatient', 'carrier_a': 'carrier', 'carrier_b': 'carrier', 'pde': 'pde'}
LINEAGE = [('_sample_id','integer'), ('_file_year','integer'),
           ('_source_file','text'), ('_loaded_at','timestamp with time zone')]


@dataclass(frozen=True)
class SourceFile:
    path: Path
    table: str
    sample: int
    year: int | None
    columns: tuple[str, ...]
    expected_rows: int
    sha256: str
    money_totals: dict[str, int] = field(default_factory=dict)
    skipped_money_columns: tuple[str, ...] = ()


def header_of(path):
    import csv
    with path.open(newline='', encoding='utf-8') as stream:
        try:
            header = next(csv.reader(stream))
        except StopIteration as exc:
            raise ValueError(f'Empty CSV: {path.name}') from exc
    normalized = [name.lower() for name in header]
    if (not header or any(not name or name != name.strip() for name in header)
            or len(normalized) != len(set(normalized))
            or any(name.startswith('_') for name in normalized)):
        raise ValueError(f'Invalid or colliding CSV header: {path.name}')
    return header


def build_plan(root, data_dir, profile_path, manifest_path, expected_sample=None):
    profile = json.loads(profile_path.read_text())
    if any('fixture_expected_rows' in f for f in profile['files'].values()):
        from ingest.runtime import guard
        guard()
        if not (root/'.fixture-runtime').is_file():
            raise ValueError('Fixture profile is only allowed in an isolated runtime')
    if set(profile['files']) != set(TABLES):
        raise ValueError('Profile must contain all eight supported source file types')
    sample = profile['sample']
    if expected_sample is not None and sample != expected_sample:
        raise ValueError('Profile sample metadata differs from selected sample')
    manifest = read_manifest(manifest_path)
    plan, headers = [], {}
    for kind, table in TABLES.items():
        info = profile['files'][kind]
        name = info['file']
        if Path(name).name != name:
            raise ValueError('Profile contains an unsafe source filename')
        path = data_dir / f'sample_{sample}' / name
        relative = path.relative_to(root).as_posix()
        record = manifest.get(relative)
        if not record or record['sha256'] != profile['input_sha256'].get(relative):
            raise ValueError(f'Profile and manifest provenance disagree: {name}')
        if int(record['sample_id']) != sample or record['file_type'] != kind:
            raise ValueError(f'Manifest identity mismatch: {name}')
        verify_record(path, record)
        header = header_of(path)
        if header != info['columns']:
            raise ValueError(f'Header differs from profiled source: {name}')
        columns = tuple(col.lower() for col in header)
        if table in headers and columns != headers[table]:
            raise ValueError(f'Headers disagree across {table} source files')
        headers[table] = columns
        expected = info.get('fixture_expected_rows', info['cms_expected_rows'])
        matches = info.get('fixture_row_count_matches', info['cms_row_count_matches'])
        if not matches or info['rows'] != expected:
            raise ValueError(f'Unreconciled profile row count: {name}')
        money = {col.lower(): values['total_cents'] for col, values in info.get('money',{}).items()
                 if values['invalid'] == 0}
        skipped = tuple(col.lower() for col, values in info.get('money',{}).items() if values['invalid'])
        plan.append(SourceFile(path, table, sample,
            int(kind[-4:]) if table == 'beneficiary' else None,
            columns, info['rows'], record['sha256'], money, skipped))
    return plan


def validate_table(conn, schema, source):
    observed = conn.execute('''SELECT column_name,data_type FROM information_schema.columns
        WHERE table_schema=%s AND table_name=%s ORDER BY ordinal_position''',
        (schema,source.table)).fetchall()
    expected = [(name,'text') for name in source.columns] + LINEAGE
    if observed != expected:
        raise ValueError(f'Unexpected table schema: {schema}.{source.table}; no destructive migration attempted')
    persistence = conn.execute('''SELECT c.relpersistence FROM pg_class c
        JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=%s AND c.relname=%s''',
        (schema,source.table)).fetchone()
    if persistence != ('u',):
        raise ValueError(f'Expected UNLOGGED table: {schema}.{source.table}')


def prepare_table(conn, schema, source):
    table = sql.Identifier(schema,source.table)
    definitions = sql.SQL(', ').join(sql.SQL('{} TEXT').format(sql.Identifier(c)) for c in source.columns)
    conn.execute(sql.SQL('''CREATE UNLOGGED TABLE IF NOT EXISTS {} ({},
        _sample_id INTEGER NOT NULL, _file_year INTEGER,
        _source_file TEXT NOT NULL, _loaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP)''').format(table,definitions))
    validate_table(conn,schema,source)
    # No CASCADE, dropping, or implicit migrations; downstream dependencies remain.
    conn.execute(sql.SQL('TRUNCATE TABLE {}').format(table))


def copy_file(conn, schema, source):
    table = sql.Identifier(schema,source.table)
    columns = sql.SQL(', ').join(map(sql.Identifier,source.columns))
    for col,value in [('_sample_id',source.sample),('_file_year',source.year),('_source_file',source.path.name)]:
        conn.execute(sql.SQL('ALTER TABLE {} ALTER COLUMN {} SET DEFAULT {}').format(
            table,sql.Identifier(col),sql.Literal(value)))
    # FORCE_NOT_NULL preserves empty CSV fields as text, including unquoted blanks.
    command = sql.SQL('''COPY {} ({}) FROM STDIN WITH
        (FORMAT CSV, HEADER TRUE, ENCODING 'UTF8', FORCE_NOT_NULL ({}))''').format(table,columns,columns)
    digest = hashlib.sha256()
    with conn.cursor() as cur:
        with source.path.open('rb') as stream, cur.copy(command) as copy:
            while block := stream.read(1024 * 1024):
                digest.update(block)
                copy.write(block)
        copied = cur.rowcount
    if digest.hexdigest() != source.sha256:
        raise ValueError(f'Source changed during COPY: {source.path.name}')
    if copied != source.expected_rows:
        raise ValueError(f'COPY row count mismatch for {source.path.name}: {copied} != {source.expected_rows}')
    return copied


def reconcile(conn, plan, schema='bronze'):
    records, tables = [], {}
    for table_name in dict.fromkeys(source.table for source in plan):
        sources = [s for s in plan if s.table == table_name]
        validate_table(conn,schema,sources[0])
        money_cols = sorted(set().union(*(s.money_totals for s in sources)))
        aggregates = [sql.SQL('SUM(NULLIF({}, \'\')::numeric)').format(sql.Identifier(c)) for c in money_cols]
        extra = sql.SQL(', ') + sql.SQL(', ').join(aggregates) if aggregates else sql.SQL('')
        rows = conn.execute(sql.SQL('''SELECT _source_file,_sample_id,_file_year,COUNT(*),
            MIN(_loaded_at),MAX(_loaded_at),COUNT(_loaded_at) {} FROM {}
            GROUP BY _source_file,_sample_id,_file_year ORDER BY _source_file''').format(
                extra,sql.Identifier(schema,table_name))).fetchall()
        expected = {(s.path.name,s.sample,s.year):s for s in sources}
        if {tuple(row[:3]) for row in rows} != set(expected):
            raise ValueError(f'Lineage groups do not match planned files: {table_name}')
        for row in rows:
            source = expected[tuple(row[:3])]
            if row[3] != source.expected_rows or row[6] != row[3] or row[4] != row[5]:
                raise ValueError(f'Row counts or load timestamps disagree: {source.path.name}')
            sums = {col:int((value or Decimal(0))*100) for col,value in zip(money_cols,row[7:])}
            if any(sums[col] != total for col,total in source.money_totals.items()):
                raise ValueError(f'Financial source totals differ: {source.path.name}')
            records.append(dict(table=f'{schema}.{table_name}', source_file=source.path.name,
                sample_id=source.sample, file_year=source.year, source_sha256=source.sha256,
                expected_rows=source.expected_rows, loaded_rows=row[3], difference=row[3]-source.expected_rows,
                loaded_at_utc=row[4].astimezone(timezone.utc).isoformat(), money_totals_cents=sums,
                skipped_money_columns=list(source.skipped_money_columns)))
        tables[table_name] = dict(expected_rows=sum(s.expected_rows for s in sources),
            loaded_rows=sum(row[3] for row in rows), source_columns=len(sources[0].columns),
            source_types='text', persistence='unlogged')
    return dict(tables=tables,files=records,total_loaded_rows=sum(r['loaded_rows'] for r in records),
                all_counts_match=True,all_lineage_matches=True,financial_totals_match=True)


def validate_combined_plan(plan):
    if not plan:
        raise ValueError('Empty load plan')
    columns = {}
    identities = set()
    for source in plan:
        if source.table in columns and columns[source.table] != source.columns:
            raise ValueError(f'Cross-sample column mismatch: {source.table}')
        columns[source.table] = source.columns
        identity = (source.sample, source.path.name)
        if identity in identities:
            raise ValueError(f'Duplicate source in load plan: {identity}')
        identities.add(identity)
    return plan


def load_plan(conn, plan, schema='bronze'):
    """Caller supplies an idle connection; transaction commits only after checks pass."""
    validate_combined_plan(plan)
    from psycopg.pq import TransactionStatus
    if conn.info.transaction_status != TransactionStatus.IDLE:
        raise ValueError('Loader requires an idle connection for its atomic transaction')
    with conn.transaction():
        conn.execute("SET LOCAL lock_timeout = '10s'")
        locked = conn.execute('SELECT pg_try_advisory_xact_lock(913031,hashtext(%s))',(schema,)).fetchone()[0]
        if not locked:
            raise RuntimeError('Another bronze load is already running for this schema')
        conn.execute(sql.SQL('CREATE SCHEMA IF NOT EXISTS {}').format(sql.Identifier(schema)))
        for table_name in dict.fromkeys(source.table for source in plan):
            sources = [source for source in plan if source.table == table_name]
            prepare_table(conn,schema,sources[0])
            for source in sources:
                count=copy_file(conn,schema,source)
                print(f'COPY {source.path.name}: {count:,} rows',flush=True)
            for col in ['_sample_id','_file_year','_source_file']:
                conn.execute(sql.SQL('ALTER TABLE {} ALTER COLUMN {} DROP DEFAULT').format(
                    sql.Identifier(schema,table_name),sql.Identifier(col)))
            conn.execute(sql.SQL('ANALYZE {}').format(sql.Identifier(schema,table_name)))
        result = reconcile(conn,plan,schema)
    return result


def markdown_report(report):
    lines=['# Bronze load reconciliation','',
        'The five bronze tables retain every source column as text, plus sample, file,',
        'file-year, and load-time lineage. Source blanks remain empty strings.',
        'No eligibility filtering, claim collapsing, or type conversion was applied.','',
        '| Table | Source rows | PostgreSQL rows | Difference | Raw columns |',
        '| --- | ---: | ---: | ---: | ---: |']
    for name,r in report['tables'].items():
        lines.append(f"| bronze.{name} | {r['expected_rows']:,} | {r['loaded_rows']:,} | {r['loaded_rows']-r['expected_rows']:,} | {r['source_columns']} |")
    lines += ['', '## File-level checks','',
        '| Source file | Sample | File year | Source rows | PostgreSQL rows | Difference |',
        '| --- | ---: | --- | ---: | ---: | ---: |']
    for r in report['files']:
        lines.append(f"| {r['source_file']} | {r['sample_id']} | {r['file_year'] or 'N/A'} | {r['expected_rows']:,} | {r['loaded_rows']:,} | {r['difference']:,} |")
    lines += ['', f"Total rows loaded: **{report['total_loaded_rows']:,}**.", '',
        'All per-file financial sums checked against Step 2 agree. Carrier checks cover',
        'all 13 payment and all 13 allowed columns, without excluding blank-HCPCS slots.',
        'The JSON records each exact sum in integer cents and the corresponding source hash.',
        'These are raw reconciliation totals, not finalized cost measures.','',
        'The transaction commits only after COPY counts, grouped database counts, lineage,',
        'column types, UNLOGGED status, and financial totals pass. Each file also has its',
        'SHA-256 recalculated during transmission.','',
        'Run `make verify-bronze` to recheck the current database without reloading it.',
        'UNLOGGED tables can be truncated after a crash; rerun `make bronze` to rebuild.',
        'Source files and their manifest remain the recovery source.','']
    return '\n'.join(lines)


def main():
    load_dotenv(ROOT/'.env',override=False)
    from ingest.samples import add_samples_argument, evidence_path
    parser=argparse.ArgumentParser(description=__doc__)
    add_samples_argument(parser)
    parser.add_argument('--verify-only',action='store_true')
    parser.add_argument('--plan-only',action='store_true')
    parser.add_argument('--data-dir',type=Path,default=Path(os.getenv('DATA_DIR','data/extracted')))
    args=parser.parse_args()
    data_dir=args.data_dir if args.data_dir.is_absolute() else ROOT/args.data_dir
    started=time.monotonic()
    plan=validate_combined_plan([source for sample in args.samples
        for source in build_plan(ROOT,data_dir,evidence_path(ROOT,'data_profile',sample),ROOT/'data/manifest.csv',expected_sample=sample)])
    if args.plan_only:
        for source in plan:print(source.table,source.path.name,source.expected_rows)
        return
    with get_conn() as conn:
        report=reconcile(conn,plan) if args.verify_only else load_plan(conn,plan)
    report.update(verified_at_utc=datetime.now(timezone.utc).isoformat(),
                  operation='verify-only' if args.verify_only else 'load',
                  elapsed_seconds=round(time.monotonic()-started,2), samples=args.samples)
    report_path=ROOT/'docs/bronze_reconciliation.json'
    temporary=report_path.with_suffix('.json.part')
    temporary.write_text(json.dumps(report,indent=2)+'\n');temporary.replace(report_path)
    (ROOT/'docs/bronze_reconciliation.md').write_text(markdown_report(report))
    print(f"PASS: {report['total_loaded_rows']:,} rows reconciled across five bronze tables ({report['elapsed_seconds']}s)")


if __name__=='__main__':
    main()
