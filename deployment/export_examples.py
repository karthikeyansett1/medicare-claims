"""Run approved SQL through hosted read-only role, export aggregate demo cards."""
import sys,json,datetime
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from deployment.examples import EXAMPLES
from dotenv import dotenv_values
import psycopg
from psycopg.rows import dict_row
ROOT=Path(__file__).resolve().parents[1]
try:
 with psycopg.connect(dotenv_values(ROOT/'.env')['DEPLOY_ASSISTANT_DATABASE_URL'],row_factory=dict_row) as c:
  results=[dict(id=i,question=q,sql=s,rows=c.execute(s).fetchall()) for i,q,s in EXAMPLES]
 (ROOT/'deployment/demo_results.json').write_text(json.dumps({'verified_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'mode':'Verified static results, not live or AI-generated','scope':'Sample 1 · deterministic 1,000-member fixture','examples':results},default=str,indent=2)+'\n')
 print('Verified',len(results),'aggregate examples against hosted read-only database')
except Exception as e: print(type(e).__name__);raise SystemExit(1)
