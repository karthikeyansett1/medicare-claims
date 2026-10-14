"""Owner-only deployment: copy seven approved fixture tables into an EMPTY Neon DB.
Run locally; admin DSN is read from ignored .env and never printed.
"""
import hashlib, json, secrets, subprocess
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, quote
from dotenv import dotenv_values, set_key
import psycopg
from psycopg import sql
ROOT=Path(__file__).resolve().parents[1]
TABLES=['gold.dim_member_year','gold.dim_provider','gold.fct_member_year_cost','gold.attribution_long','gold.fct_readmissions','marts.mart_provider_performance','marts.mart_cost_by_ccs']
CONTAINER='medicare-step15-freshproof-db-1'
def docker(*args):
 return subprocess.check_output(['docker','exec',CONTAINER,*args])
def main():
 env=ROOT/'.env'; values=dotenv_values(env)
 with psycopg.connect(values['DEPLOY_DATABASE_URL']) as c:
  existing=c.execute("select schemaname,tablename from pg_tables where schemaname not in ('pg_catalog','information_schema')").fetchall()
  if existing: raise ValueError('Hosted database must be empty; refusing overwrite.')
  c.execute('CREATE SCHEMA gold; CREATE SCHEMA marts')
  dump=docker('pg_dump','-U','medicare','-d','medicare_ci','--schema-only','--no-owner','--no-privileges',*[v for t in TABLES for v in ('-t',t)]).decode()
  dump='\n'.join(l for l in dump.splitlines() if not l.startswith('\\'))
  c.execute(dump)
  counts={}
  for t in TABLES:
   csv=docker('psql','-U','medicare','-d','medicare_ci','-c',f'COPY {t} TO STDOUT WITH CSV')
   with c.cursor().copy(sql.SQL('COPY {} FROM STDIN WITH CSV').format(sql.Identifier(*t.split('.')))) as copy: copy.write(csv)
   counts[t]={'rows':c.execute(sql.SQL('SELECT count(*) FROM {}').format(sql.Identifier(*t.split('.')))).fetchone()[0],'csv_sha256':hashlib.sha256(csv).hexdigest()}
   with c.cursor().copy(sql.SQL('COPY {} TO STDOUT WITH CSV').format(sql.Identifier(*t.split('.')))) as copy: remote=b''.join(bytes(x) for x in copy)
   if csv != remote: raise ValueError('Hosted COPY verification mismatch')
  password=secrets.token_urlsafe(36)
  if c.execute("select 1 from pg_roles where rolname='medicare_demo_ro'").fetchone(): raise ValueError('Unexpected existing role')
  c.execute(sql.SQL('CREATE ROLE medicare_demo_ro LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION').format(sql.Literal(password)))
  c.execute('ALTER ROLE medicare_demo_ro SET default_transaction_read_only=on; ALTER ROLE medicare_demo_ro SET statement_timeout=20000')
  db=c.execute('select current_database()').fetchone()[0]
  c.execute(sql.SQL('REVOKE TEMPORARY ON DATABASE {} FROM PUBLIC').format(sql.Identifier(db)))
  c.execute('REVOKE CREATE ON SCHEMA public FROM PUBLIC; GRANT USAGE ON SCHEMA gold,marts TO medicare_demo_ro')
  c.execute(sql.SQL('GRANT CONNECT ON DATABASE {} TO medicare_demo_ro').format(sql.Identifier(db)))
  for t in TABLES: c.execute(sql.SQL('GRANT SELECT ON {} TO medicare_demo_ro').format(sql.Identifier(*t.split('.'))))
  size=c.execute('select pg_database_size(current_database())').fetchone()[0]
 parts=urlsplit(values['DEPLOY_DATABASE_URL']); netloc='medicare_demo_ro:'+quote(password,safe='')+'@'+parts.netloc.split('@')[-1]
 dsn=urlunsplit(parts._replace(netloc=netloc)); env.chmod(0o600); set_key(str(env),'DEPLOY_ASSISTANT_DATABASE_URL',dsn)
 with psycopg.connect(dsn) as c:
  grants=c.execute("select table_schema,table_name,privilege_type from information_schema.role_table_grants where grantee=current_user order by 1,2,3").fetchall()
  if len(grants)!=7 or any(g[2]!='SELECT' for g in grants): raise ValueError('Unexpected grants')
  c.execute('SET default_transaction_read_only=off'); c.commit()
  try:
   c.execute('INSERT INTO marts.mart_cost_by_ccs SELECT * FROM marts.mart_cost_by_ccs WHERE false')
  except psycopg.errors.InsufficientPrivilege: c.rollback()
  else: raise ValueError('Write privilege unexpectedly permitted')
 manifest={'scope':'Sample 1 deterministic 1,000-member fixture; 2008–2010 source years, 2009–2010 provider performance','tables':counts,'database_bytes':size,'copy_bytes_verified':True,'readonly_grants_verified':True,'insert_denied':True,'llm_enabled':False}
 (ROOT/'deployment/database_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print(json.dumps(manifest,indent=2))
if __name__=='__main__':
 try: main()
 except Exception as e: print('Deployment failed:',type(e).__name__); raise SystemExit(1)
