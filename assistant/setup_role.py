"""Idempotent least-privilege setup. Run as warehouse owner, never from the UI."""
import os
import secrets
from dotenv import dotenv_values, set_key
from psycopg import sql
from ingest.db import ROOT, get_conn, connection_settings
from assistant.guardrails import TABLES


def setup_role():
    settings = connection_settings()
    path = ROOT / '.env'
    values = dotenv_values(path)
    password = os.getenv('ASSISTANT_PG_PASSWORD') or values.get('ASSISTANT_PG_PASSWORD')
    if not password:
        password = secrets.token_urlsafe(36)
        path.touch(mode=0o600, exist_ok=True)
        path.chmod(0o600)
        set_key(str(path), 'ASSISTANT_PG_PASSWORD', password)
    if path.exists():
        path.chmod(0o600)
    with get_conn() as conn:
        conn.execute((ROOT / 'sql/roles.sql').read_text())
        # Literal performs PostgreSQL escaping; do not log composed DDL.
        conn.execute(sql.SQL('ALTER ROLE assistant_ro PASSWORD {}').format(sql.Literal(password)))
        conn.execute(sql.SQL('GRANT CONNECT ON DATABASE {} TO assistant_ro').format(sql.Identifier(settings['dbname'])))
        # PUBLIC TEMP/CREATE would bypass per-role revocations. This project DB is dedicated.
        conn.execute(sql.SQL('REVOKE TEMPORARY ON DATABASE {} FROM PUBLIC').format(sql.Identifier(settings['dbname'])))
        conn.execute('REVOKE CREATE ON SCHEMA public FROM PUBLIC')
        for schema in ('bronze','staging','silver','gold','marts','analysis','reference','public'):
            exists = conn.execute('SELECT EXISTS(SELECT FROM pg_namespace WHERE nspname=%s)', (schema,)).fetchone()[0]
            if not exists:
                continue
            conn.execute(sql.SQL('REVOKE ALL ON ALL TABLES IN SCHEMA {} FROM assistant_ro').format(sql.Identifier(schema)))
            conn.execute(sql.SQL('REVOKE ALL ON SCHEMA {} FROM assistant_ro').format(sql.Identifier(schema)))
            # Explicitly remove PUBLIC execution of application-defined functions, including definer functions.
            conn.execute(sql.SQL('REVOKE EXECUTE ON ALL FUNCTIONS IN SCHEMA {} FROM PUBLIC, assistant_ro').format(sql.Identifier(schema)))
            conn.execute(sql.SQL('ALTER DEFAULT PRIVILEGES IN SCHEMA {} REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC').format(sql.Identifier(schema)))
        for schema in ('gold','marts'):
            if conn.execute('SELECT EXISTS(SELECT FROM pg_namespace WHERE nspname=%s)',(schema,)).fetchone()[0]:
                conn.execute(sql.SQL('GRANT USAGE ON SCHEMA {} TO assistant_ro').format(sql.Identifier(schema)))
        for table in TABLES:
            if conn.execute('SELECT to_regclass(%s)', (table,)).fetchone()[0]:
                conn.execute(sql.SQL('GRANT SELECT ON {} TO assistant_ro').format(sql.Identifier(*table.split('.'))))
    print('PASS: assistant_ro configured with exact analytics SELECT grants; local secret stored privately.')


if __name__ == '__main__':
    setup_role()
