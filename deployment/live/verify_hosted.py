"""Owner verification after bootstrap. No API calls; all probe writes roll back.

Run as a module with --probe-rollback after owner authorization. Sequence IDs may
advance (PostgreSQL sequences are nontransactional), but rows/spend stay unchanged.
The admin DSN is read only by this local verifier, never deployed with the app.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tomllib
import psycopg
import certifi
from dotenv import dotenv_values
from assistant.live_app import Config, verify_runtime
from assistant.live_budget import CAMPAIGN

ROOT = Path(__file__).resolve().parents[2]
RESERVE = 'SELECT live_budget.reserve(%s,%s,%s,%s)'
PARAMS = (CAMPAIGN, 8192, 1, 102450)


@contextmanager
def rolled_back(dsn):
    conn = psycopg.connect(dsn, connect_timeout=15, sslmode='verify-full', sslrootcert=certifi.where())
    try:
        conn.execute("SET LOCAL statement_timeout='8s'")
        conn.execute("SET LOCAL lock_timeout='2s'")
        yield conn
    finally:
        conn.rollback()
        conn.close()


def denied(conn, command, params=None, expected='42501'):
    """A failed SAVEPOINT probe must match the expected SQLSTATE."""
    conn.execute('SAVEPOINT denied_probe')
    try:
        conn.execute(command, params)
    except psycopg.Error as error:
        state = error.sqlstate
        conn.execute('ROLLBACK TO SAVEPOINT denied_probe')
        conn.execute('RELEASE SAVEPOINT denied_probe')
        if state != expected:
            raise AssertionError('Unexpected rejection class') from None
    else:
        conn.execute('ROLLBACK TO SAVEPOINT denied_probe')
        conn.execute('RELEASE SAVEPOINT denied_probe')
        raise AssertionError('Forbidden operation unexpectedly succeeded')


def snapshot(admin):
    with rolled_back(admin) as conn:
        return tuple(conn.execute('SELECT campaign_id,cap_microdollars,spent_microdollars FROM live_budget.campaign').fetchone()) + (conn.execute('SELECT count(*) FROM live_budget.reservations').fetchone()[0],)


def verify(cfg, admin):
    checks = []
    verify_runtime(cfg)
    checks.append('runtime_roles_effective_privileges_tls_fixture')
    before = snapshot(admin)
    # Require a quiet unused campaign: never run probes against active visitors.
    if before != (CAMPAIGN, 5000000, 0, 0):
        raise AssertionError('Verifier requires an unused campaign before live activation')
    try:
        with rolled_back(cfg.query_dsn) as conn:
            # Disable role default to prove permissions independently of READ ONLY.
            conn.execute('SET TRANSACTION READ WRITE')
            denied(conn, 'INSERT INTO marts.mart_cost_by_ccs SELECT * FROM marts.mart_cost_by_ccs WHERE false')
            denied(conn, RESERVE, PARAMS)
        checks.append('query_role_write_and_budget_execution_denied')
        with rolled_back(cfg.budget_dsn) as conn:
            for command in [
                'SELECT * FROM gold.dim_member_year LIMIT 0',
                'UPDATE live_budget.campaign SET spent_microdollars=0 WHERE false',
                'DELETE FROM live_budget.reservations WHERE false',
                'CREATE TABLE live_budget.unauthorized_probe(id integer)',
                'CREATE TEMP TABLE unauthorized_probe(id integer)',
                'SET LOCAL ROLE medicare_live_owner',
            ]:
                denied(conn, command)
            denied(conn, RESERVE, (CAMPAIGN,8192,1,1), 'P0001')
            denied(conn, RESERVE, ('other',8192,1,102450), 'P0001')
            for _ in range(3):
                assert conn.execute(RESERVE, PARAMS).fetchone()[0] > 0
            assert conn.execute('SELECT * FROM live_budget.status()').fetchone()[2] == 307350
            denied(conn, RESERVE, PARAMS, 'P0001')
        checks.append('budget_least_privilege_cost_campaign_and_minute_limit')
        # Owner-only temporary fixtures; runtime role cannot perform this setup.
        # The fixed SECURITY DEFINER body is identical for all callers. Real
        # budget-login execution/denials/concurrency are verified separately.
        with rolled_back(admin) as conn:
            conn.execute('UPDATE live_budget.campaign SET spent_microdollars=4999999')
            conn.execute('SET LOCAL ROLE medicare_live_owner')
            denied(conn, RESERVE, PARAMS, 'P0001')
        checks.append('owner_transaction_fixture_lifetime_cap_rejects_before_reservation')
        with rolled_back(admin) as conn:
            conn.execute("INSERT INTO live_budget.reservations(created_at,input_bound,output_bound,microdollars) SELECT clock_timestamp()-interval '2 hours',8192,1,102450 FROM generate_series(1,30)")
            conn.execute('SET LOCAL ROLE medicare_live_owner')
            denied(conn, RESERVE, PARAMS, 'P0001')
        checks.append('owner_transaction_fixture_rolling_day_limit')
        with rolled_back(cfg.budget_dsn) as first:
            first.execute(RESERVE, PARAMS)
            with rolled_back(cfg.budget_dsn) as second:
                second.execute("SET LOCAL lock_timeout='500ms'")
                denied(second, RESERVE, PARAMS, '55P03')
        checks.append('separate_connections_serialize_on_campaign_row')
    finally:
        after = snapshot(admin)
        if before != after:
            raise AssertionError('Campaign spend or reservation rows changed during probes')
    checks.append('all_probe_rows_and_spend_rolled_back')
    return {'verified_at_utc':datetime.now(timezone.utc).isoformat(),'checks':checks,
            'all_passed':True,'api_calls':0,'cap_microdollars':before[1],
            'spent_before':before[2],'spent_after':after[2],
            'reservation_rows_before':before[3],'reservation_rows_after':after[3],
            'sequence_note':'Identity sequence values may advance during rolled-back probes; no allowance is spent.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe-rollback',action='store_true',required=True)
    parser.add_argument('--secrets',type=Path,default=ROOT/'.runtime/streamlit-live-secrets.toml')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    cfg=Config.from_mapping(tomllib.loads(args.secrets.read_text()))
    admin={**dotenv_values(ROOT/'.env'),**os.environ}['DEPLOY_DATABASE_URL']
    result=verify(cfg,admin)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    try:
        main()
    except Exception as error:
        print('Hosted verification failed:',type(error).__name__,'(details suppressed).')
        raise SystemExit(1)
