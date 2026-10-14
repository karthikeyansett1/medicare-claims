"""Dedicated runtime connection: no administrator credential fallback."""
import os
import json
import time
from dotenv import load_dotenv
import psycopg
from psycopg.rows import dict_row
from ingest.db import ROOT
from assistant.guardrails import validate_sql, GuardrailError


def connect():
    load_dotenv(ROOT / '.env', override=False)
    dsn = os.getenv('ASSISTANT_DATABASE_URL')
    if dsn:
        return psycopg.connect(dsn, connect_timeout=10, row_factory=dict_row,
            options='-c default_transaction_read_only=on -c statement_timeout=20000 -c search_path=pg_catalog')
    password = os.getenv('ASSISTANT_PG_PASSWORD')
    if not password:
        raise ValueError('Run assistant role setup before using the assistant.')
    return psycopg.connect(host=os.getenv('PG_HOST', 'localhost'), port=int(os.getenv('PG_PORT', '5432')),
                           dbname=os.getenv('PG_DB', 'medicare'), user='assistant_ro', password=password,
                           connect_timeout=10, row_factory=dict_row,
                           options='-c default_transaction_read_only=on -c statement_timeout=20000 -c search_path=pg_catalog')


def execute(sql):
    checked = validate_sql(sql)
    with connect() as conn:
        conn.execute('SET TRANSACTION READ ONLY')
        conn.execute("SET LOCAL statement_timeout = '20s'")
        conn.execute("SET LOCAL lock_timeout = '2s'")
        deadline = time.monotonic() + 20
        # A server cursor avoids buffering the full 500-row result at the client.
        with conn.cursor(name='assistant_result') as cur:
            cur.execute(checked)
            # dict_row cannot preserve two output values with the same label.
            names = [column.name for column in cur.description]
            if len(names) != len(set(names)):
                raise GuardrailError('Result columns must have unique names; alias each repeated expression.')
            rows = []
            size = 0
            for _ in range(500):
                remaining_ms = int((deadline - time.monotonic()) * 1000)
                if remaining_ms <= 0:
                    raise GuardrailError('Query exceeded its 20-second execution deadline.')
                conn.execute("SELECT set_config('statement_timeout', %s, true)", (str(remaining_ms),))
                row = cur.fetchone()
                if time.monotonic() > deadline:
                    raise GuardrailError('Query exceeded its 20-second execution deadline.')
                if row is None:
                    break
                row_size = len(json.dumps(row, default=str).encode('utf-8'))
                size += row_size
                if row_size > 64000 or size > 1000000:
                    raise GuardrailError('Result exceeds row/total byte limits; select fewer columns or aggregate.')
                rows.append(row)
    return checked, rows
