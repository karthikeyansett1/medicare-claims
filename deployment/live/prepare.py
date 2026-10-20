"""Owner-only explicit bootstrap; never run by the app. Does not call OpenAI.
Writes secrets to ignored .runtime/streamlit-live-secrets.toml, never stdout.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
from urllib.parse import urlsplit,urlunsplit,urlencode,parse_qsl,quote
import psycopg
import certifi
from psycopg import sql
from dotenv import dotenv_values
from assistant.live_app import Config
ROOT=Path(__file__).resolve().parents[2]


def role_dsn(dsn,user,password=None):
    parts=urlsplit(dsn)
    if parts.scheme not in ('postgres','postgresql'):raise ValueError('Expected a PostgreSQL URL.')
    authority=parts.netloc.rsplit('@',1)[-1]
    if password is None:
        from urllib.parse import unquote
        password=unquote(parts.password or '')
    query=dict(parse_qsl(parts.query));query['sslmode']='verify-full';query.pop('sslrootcert',None)
    return urlunsplit(parts._replace(netloc=user+':'+quote(password,safe='')+'@'+authority,query=urlencode(query)))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply-bootstrap',action='store_true',required=True,help='Explicit owner authorization to create the one-time ledger/role.')
    parser.parse_args()
    values={**dotenv_values(ROOT/'.env'),**os.environ}
    target=ROOT/'.runtime/streamlit-live-secrets.toml'
    if target.exists():raise ValueError('Secrets file already exists; refusing bootstrap/reset.')
    target.parent.mkdir(mode=0o700,exist_ok=True)
    admin=values['DEPLOY_DATABASE_URL'];query=values['DEPLOY_ASSISTANT_DATABASE_URL']
    password=secrets.token_urlsafe(36)
    output={'LIVE_ACCESS_CODE':secrets.token_urlsafe(36),'LIVE_OPENAI_API_KEY':values['LLM_API_KEY'],
            'LIVE_QUERY_DATABASE_URL':role_dsn(query,'medicare_demo_ro'),
            'LIVE_BUDGET_DATABASE_URL':role_dsn(admin,'medicare_live_budget',password)}
    Config.from_mapping(output)
    script=(Path(__file__).parent/'bootstrap.sql').read_text().replace('BEGIN;\n','',1)
    script=script.rsplit('COMMIT;',1)[0]
    # Persist credentials durably while DDL is still uncommitted. A failed file
    # write rolls back DDL; an ambiguous commit retains credentials for recovery.
    created_file=False
    prepared=False
    try:
        with psycopg.connect(admin,connect_timeout=10,sslmode='verify-full',sslrootcert=certifi.where()) as conn:
            if conn.execute("SELECT EXISTS(SELECT 1 FROM pg_namespace WHERE nspname='live_budget') OR EXISTS(SELECT 1 FROM pg_roles WHERE rolname IN ('medicare_live_owner','medicare_live_budget'))").fetchone()[0]:
                raise ValueError('Existing live campaign/role; refusing reinitialization.')
            conn.execute(script)
            conn.execute(sql.SQL('ALTER ROLE medicare_live_budget PASSWORD {}').format(sql.Literal(password)))
            conn.execute(sql.SQL('GRANT CONNECT ON DATABASE {} TO medicare_live_budget').format(sql.Identifier(conn.info.dbname)))
            fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            created_file=True
            with os.fdopen(fd,'w') as stream:
                stream.write('\n'.join(k+' = '+json.dumps(v) for k,v in output.items())+'\n')
                stream.flush()
                os.fsync(stream.fileno())
            # Persist the directory entry as well as the file contents.
            directory_fd=os.open(target.parent,os.O_RDONLY)
            try:os.fsync(directory_fd)
            finally:os.close(directory_fd)
            prepared=True
            # Context exit commits only after secrets are durable.
    except Exception:
        if created_file and not prepared:
            target.unlink(missing_ok=True)
        # If commit acknowledgement was lost, preserve the private file. The
        # next invocation refuses both existing file and existing campaign.
        raise
    print('Created one-time live budget and private secrets file. Keys: '+', '.join(output))
    print('Secrets path: .runtime/streamlit-live-secrets.toml (mode 600). No API calls made.')

if __name__=='__main__':
    try:main()
    except Exception as error:
        print('Preparation failed:',type(error).__name__,'(details suppressed to protect credentials).')
        raise SystemExit(1)
