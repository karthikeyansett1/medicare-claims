"""Opt-in integration checks, never insert into warehouse tables."""
import os
import uuid
import pytest
import psycopg
from psycopg import sql
import yaml
from assistant.database import connect, execute
from assistant.guardrails import TABLES
from ingest.db import get_conn, ROOT

pytestmark=pytest.mark.skipif(os.getenv('RUN_DB_TESTS')!='1',reason='requires local PostgreSQL')


def test_schema_matches_semantics():
    with get_conn() as conn:
        for name,meta in TABLES.items():
            schema,table=name.split('.')
            actual={x[0] for x in conn.execute('SELECT column_name FROM information_schema.columns WHERE table_schema=%s AND table_name=%s',(schema,table))}
            assert actual==set(meta['columns'])
            assert all(c['meaning'] for c in meta['columns'].values())


def test_readonly_and_exact_grants():
    with connect() as conn:
        assert conn.execute('SHOW default_transaction_read_only').fetchone()['default_transaction_read_only']=='on'
        assert conn.execute('SHOW statement_timeout').fetchone()['statement_timeout']=='20s'
        for table in TABLES:
            privileges=conn.execute("SELECT has_table_privilege(current_user,%s,'SELECT') AS r, has_table_privilege(current_user,%s,'INSERT,UPDATE,DELETE,TRUNCATE') AS w",(table,table)).fetchone()
            assert privileges=={'r':True,'w':False}
        rows=conn.execute("SELECT n.nspname || '.' || c.relname AS name FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname NOT IN ('pg_catalog','information_schema') AND c.relkind IN ('r','v','m') AND has_table_privilege(current_user,c.oid,'SELECT')").fetchall()
        assert {r['name'] for r in rows}==set(TABLES)


def test_insert_denied_even_if_readonly_disabled():
    schema='assistant_permission_'+uuid.uuid4().hex[:12]
    with get_conn() as admin:
        admin.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
        admin.execute(sql.SQL('CREATE TABLE {}.probe (value integer)').format(sql.Identifier(schema)))
        admin.execute(sql.SQL('GRANT USAGE ON SCHEMA {} TO assistant_ro').format(sql.Identifier(schema)))
        admin.execute(sql.SQL('GRANT SELECT ON {}.probe TO assistant_ro').format(sql.Identifier(schema)))
    try:
        with connect() as conn:
            with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
                conn.execute(sql.SQL('INSERT INTO {}.probe VALUES (1)').format(sql.Identifier(schema)))
        with connect() as conn:
            conn.execute('SET TRANSACTION READ WRITE')
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                conn.execute(sql.SQL('INSERT INTO {}.probe VALUES (1)').format(sql.Identifier(schema)))
    finally:
        with get_conn() as admin:
            admin.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))


def test_eight_few_shots_execute():
    examples=yaml.safe_load((ROOT/'assistant/few_shot.yaml').read_text())['examples']
    assert len(examples)==8
    for example in examples:
        checked,rows=execute(example['sql'])
        assert len(rows)<=500
        assert rows


def test_duplicate_result_labels_rejected_before_dictionary_loss():
    from assistant.guardrails import GuardrailError
    with pytest.raises(GuardrailError, match='unique names'):
        execute('SELECT COUNT(*), COUNT(*) FROM gold.dim_member_year')
    _, rows = execute('SELECT COUNT(*) AS first_count, COUNT(*) AS second_count FROM gold.dim_member_year')
    assert len(rows[0]) == 2
    assert rows[0]['first_count'] == rows[0]['second_count']
