"""Access-gated fixture assistant; imported safely without Streamlit or network calls."""
from dataclasses import dataclass, field
import hashlib
import hmac
import json
import re
import unicodedata
from pathlib import Path
import time
import psycopg
import certifi
from psycopg.conninfo import conninfo_to_dict
from psycopg.rows import dict_row
from openai import OpenAI, APIError
from assistant.sql_agent import Agent, AssistantError, Plan
from assistant.guardrails import validate_sql, GuardrailError, TABLES
from assistant.live_budget import MODEL, BudgetedClient, PostgresBudget, LiveUnavailable

SCOPE = 'Sample 1 deterministic 1,000-member synthetic fixture only; not the full CMS samples.'
SCOPE_RULES = '''DEPLOYMENT SCOPE OVERRIDE: Only the deterministic 1,000-member Sample 1 synthetic fixture is loaded. Never describe results as the full Sample 1, full warehouse, all CMS samples, or Sample 2. CCS pooled results mean only this loaded Sample 1 fixture. Explain this fixture scope in every answer and assumptions. Return clarification with empty SQL for any request requiring Sample 2, multiple samples, or full-sample estimates. Performance years 2009/2010 are supported; source dates may include 2008. No claim of general population representativeness is supported.'''
ROOT=Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Config:
    access_code: str = field(repr=False)
    api_key: str = field(repr=False)
    query_dsn: str = field(repr=False)
    budget_dsn: str = field(repr=False)

    @classmethod
    def from_mapping(cls, values):
        try:
            cfg=cls(*(str(values[k]) for k in ('LIVE_ACCESS_CODE','LIVE_OPENAI_API_KEY','LIVE_QUERY_DATABASE_URL','LIVE_BUDGET_DATABASE_URL')))
            if not re.fullmatch(r'[A-Za-z0-9_-]{43,128}',cfg.access_code) or len(set(cfg.access_code)) < 16 or 'REPLACE' in cfg.access_code.upper():
                raise ValueError()
            if not cfg.api_key.strip(): raise ValueError()
            q,b=conninfo_to_dict(cfg.query_dsn),conninfo_to_dict(cfg.budget_dsn)
            for settings,user in ((q,'medicare_demo_ro'),(b,'medicare_live_budget')):
                if settings.get('user')!=user or not settings.get('password') or settings.get('sslmode')!='verify-full' or settings.get('sslrootcert'): raise ValueError()
                if not settings.get('host') or not settings.get('dbname'): raise ValueError()
            if any(q.get(k)!=b.get(k) for k in ('host','port','dbname')): raise ValueError()
            return cfg
        except Exception:
            raise LiveUnavailable('Live assistant configuration is unavailable.') from None


def authorized(code, cfg):
    return isinstance(code,str) and hmac.compare_digest(hashlib.sha256(code.encode()).digest(),hashlib.sha256(cfg.access_code.encode()).digest())


def fixture_clarification(question):
    text=unicodedata.normalize('NFKC',question).casefold()
    if re.search(r'\bsamples?\s*(?:#\s*)?(?:2|two|ii|1\s*(?:and|&|,|\+)\s*2)\b|\b(?:second|2nd)\s+sample\b|\b(?:both|multiple|all|full)\s+(?:cms\s+)?samples?\b|\bfull\s+(?:dataset|warehouse|population)\b',text):
        return 'Only the deterministic 1,000-member Sample 1 fixture is available. Please ask about this fixture; Sample 2 and full-sample estimates are unavailable.'
    return None


def verify_privileges(conn, query_role):
    if conn.execute("SELECT has_database_privilege(current_user,current_database(),'CREATE,TEMP')").fetchone()[0]: raise ValueError()
    if conn.execute("SELECT EXISTS(SELECT 1 FROM pg_namespace WHERE nspname NOT LIKE 'pg_%' AND nspname<>'information_schema' AND has_schema_privilege(current_user,oid,'CREATE'))").fetchone()[0]: raise ValueError()
    relations=conn.execute("SELECT n.nspname||'.'||c.relname,has_table_privilege(current_user,c.oid,'SELECT'),has_table_privilege(current_user,c.oid,'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER') FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE c.relkind IN ('r','v','m','p','f') AND n.nspname NOT LIKE 'pg_%' AND n.nspname<>'information_schema'").fetchall()
    for name,can_select,can_write in relations:
        if can_write or (can_select and (not query_role or name not in TABLES)): raise ValueError()
    functions=conn.execute("SELECT p.proname,has_function_privilege(current_user,p.oid,'EXECUTE') FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='live_budget' ORDER BY p.proname").fetchall()
    if functions!=[('reserve',not query_role),('status',not query_role)]: raise ValueError()


def verify_runtime(cfg, connect=psycopg.connect):
    """Read-only checks after authentication; no schema creation or budget reset."""
    manifest=json.loads((ROOT/'deployment/database_manifest.json').read_text())
    try:
        with connect(cfg.query_dsn,connect_timeout=10,sslmode='verify-full',sslrootcert=certifi.where()) as conn:
            conn.execute('SET TRANSACTION READ ONLY')
            conn.execute("SET LOCAL statement_timeout='20s'")
            if conn.execute('SELECT current_user').fetchone()[0]!='medicare_demo_ro': raise ValueError()
            if conn.execute('SELECT rolsuper OR rolcreaterole OR rolcreatedb OR rolreplication OR rolbypassrls FROM pg_roles WHERE rolname=current_user').fetchone()[0]: raise ValueError()
            if conn.execute('SELECT EXISTS(SELECT 1 FROM pg_auth_members WHERE member=(SELECT oid FROM pg_roles WHERE rolname=current_user))').fetchone()[0]: raise ValueError()
            grants=conn.execute("SELECT table_schema||'.'||table_name,privilege_type FROM information_schema.role_table_grants WHERE grantee=current_user").fetchall()
            if set(grants)!={(name,'SELECT') for name in TABLES}: raise ValueError()
            verify_privileges(conn,True)
            for table in TABLES:
                # Identifiers come only from the committed allowlist.
                count=conn.execute('SELECT count(*) FROM '+table).fetchone()[0]
                if count!=manifest['tables'][table]['rows']: raise ValueError()
                if table!='marts.mart_cost_by_ccs':
                    if conn.execute('SELECT EXISTS(SELECT 1 FROM '+table+' WHERE _sample_id IS DISTINCT FROM 1)').fetchone()[0]: raise ValueError()
        with connect(cfg.budget_dsn,connect_timeout=10,sslmode='verify-full',sslrootcert=certifi.where()) as conn:
            conn.execute('SET TRANSACTION READ ONLY')
            conn.execute("SET LOCAL statement_timeout='20s'")
            if conn.execute('SELECT current_user').fetchone()[0]!='medicare_live_budget': raise ValueError()
            if conn.execute('SELECT rolsuper OR rolcreaterole OR rolcreatedb OR rolreplication OR rolbypassrls FROM pg_roles WHERE rolname=current_user').fetchone()[0]: raise ValueError()
            if conn.execute('SELECT EXISTS(SELECT 1 FROM pg_auth_members WHERE member=(SELECT oid FROM pg_roles WHERE rolname=current_user))').fetchone()[0]: raise ValueError()
            verify_privileges(conn,False)
            status=conn.execute('SELECT * FROM live_budget.status()').fetchone()
            if not status or status[0]!='sample1-fixture-live-v1' or status[1]!=5000000: raise ValueError()
    except Exception:
        raise LiveUnavailable('Deployment verification failed. No API call was sent.') from None


def execute_fixture(sql, dsn):
    checked=validate_sql(sql)
    with psycopg.connect(dsn,connect_timeout=10,row_factory=dict_row,sslmode='verify-full',sslrootcert=certifi.where()) as conn:
        conn.execute('SET TRANSACTION READ ONLY')
        conn.execute("SET LOCAL statement_timeout='20s'")
        conn.execute('SET LOCAL search_path=pg_catalog')
        conn.execute("SET LOCAL lock_timeout='2s'")
        deadline=time.monotonic()+20
        with conn.cursor(name='live_fixture_result') as cur:
            cur.execute(checked)
            names=[c.name for c in cur.description]
            if len(names)!=len(set(names)):raise GuardrailError('Result columns require unique aliases.')
            rows=[];size=0
            for _ in range(500):
                remaining=int((deadline-time.monotonic())*1000)
                if remaining<=0:raise GuardrailError('Query deadline exceeded.')
                conn.execute("SELECT set_config('statement_timeout',%s,true)",(str(remaining),))
                row=cur.fetchone()
                if row is None:break
                if time.monotonic()>deadline:raise GuardrailError('Query deadline exceeded.')
                length=len(json.dumps(row,default=str).encode());size+=length
                if length>64000 or size>1000000:raise GuardrailError('Result too large; aggregate the query.')
                rows.append(row)
    return checked,rows


class LiveAgent(Agent):
    def __init__(self,cfg,code,client_factory=OpenAI,verify=verify_runtime):
        if not authorized(code,cfg):raise LiveUnavailable('Access code required.')
        verify(cfg)
        # No environment fallback, local .env loading, admin DSN or custom API URL.
        client=client_factory(api_key=cfg.api_key,base_url='https://api.openai.com/v1',timeout=60,max_retries=0)
        self.client=BudgetedClient(client,PostgresBudget(cfg.budget_dsn))
        self.model=MODEL;self.usage=[]
        self.execute_query=lambda sql:execute_fixture(sql,cfg.query_dsn)

    def ask(self,question,sample=1,year=2009,method='A_visits'):
        if not isinstance(question,str) or not 1<=len(question.strip())<=1500:raise AssistantError('Question must contain 1–1500 characters.')
        clarification=fixture_clarification(question)
        if sample!=1 or clarification:
            return {'answer':clarification or 'Only the Sample 1 fixture is available.','sql':'','rows':[],'assumptions':[SCOPE],'usage':[],'clarification':True}
        result=super().ask(question,1,year,method)
        result['assumptions']=[SCOPE]+result['assumptions']
        result['answer']=SCOPE+'\n\n'+result['answer']
        return result

    def _call(self,messages,structured=False):
        messages=[{'role':'system','content':SCOPE_RULES}]+messages
        kwargs=dict(model=MODEL,input=messages,max_output_tokens=3000,store=False,service_tier='default',reasoning={'effort':'low'})
        if structured:
            schema=Plan.model_json_schema();schema['additionalProperties']=False
            kwargs['text']={'format':{'type':'json_schema','name':'query_plan','strict':True,'schema':schema}}
        try:response=self.client.responses.create(**kwargs)
        except APIError:raise LiveUnavailable('Provider unavailable. The reservation remains used; no automatic retry.') from None
        if response.model!=MODEL or getattr(response,'service_tier',None)!='default':raise LiveUnavailable('Unexpected provider response configuration.')
        if response.status!='completed' or not response.output_text:raise AssistantError('No completed answer within the output limit.')
        self.usage.append({'model':MODEL,'input_tokens':response.usage.input_tokens if response.usage else None,'output_tokens':response.usage.output_tokens if response.usage else None})
        return response.output_text


def render():
    import os
    import streamlit as st
    st.set_page_config(page_title='Private fixture assistant',layout='wide')
    st.title('Synthetic claims fixture assistant')
    st.caption(SCOPE)
    st.info('Access-code protected. One shared $5 lifetime API allowance; conservative reservations are never refunded. A few questions may exhaust the allowance. Hosting and database free-tier quotas still apply.')
    try:
        values=dict(os.environ)
        try:values.update(dict(st.secrets))
        except FileNotFoundError:pass
        cfg=Config.from_mapping(values)
    except Exception:
        st.error('Live assistant is not configured.');st.stop()
    # Authenticate on every request; the code is not retained in session state after submit.
    with st.form('live_question',clear_on_submit=True):
        code=st.text_input('Private access code',type='password')
        year=st.selectbox('Performance year',[2009,2010])
        method=st.selectbox('Attribution method',['A_visits','B_allowed'])
        question=st.text_area('Question about the Sample 1 fixture',max_chars=1500)
        submitted=st.form_submit_button('Ask')
    if submitted:
        st.session_state.pop('live_result',None)
        if not authorized(code,cfg):st.error('Access code is incorrect.');return
        if not question.strip():st.warning('Enter a question.');return
        try:
            with st.spinner('Checking fixture data and preparing a bounded answer…'):
                st.session_state.live_result=LiveAgent(cfg,code).ask(question,year=year,method=method)
        except (LiveUnavailable,AssistantError) as error:st.error(str(error))
        except Exception:st.error('Assistant unavailable. No further calls were sent.')
    if 'live_result' in st.session_state:
        result=st.session_state.live_result
        st.write(result['answer']);st.write('Assumptions',result['assumptions'])
        if result['sql']:st.code(result['sql'],language='sql');st.dataframe(result['rows'])
