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
    st.set_page_config(page_title='Atlas | Claims Explorer', page_icon='↗', layout='wide')
    st.markdown('''<style>
    .stApp {background:#fbf8ee;color:#24362d}
    [data-testid="stHeader"] {background:#fbf8ee}
    .block-container {max-width:1180px;padding-top:3rem;padding-bottom:3rem}
    [data-testid="stSidebar"] {background:#eff0df;border-right:1px solid #d6d8c8}
    h1,h2,h3 {color:#24362d;letter-spacing:-.035em}
    .atlas-brand {font-size:28px;font-weight:850;letter-spacing:-1px;color:#24523d}
    .atlas-brand span {color:#b94a28;margin-left:12px}
    .atlas-label {font:700 11px/1.5 monospace;letter-spacing:2px;color:#586650;margin:0 0 12px}
    .atlas-hero {border-top:2px solid #24362d;border-bottom:1px solid #b8bdaa;padding:24px 0;margin:12px 0 28px}
    .atlas-hero h1 {font:48px/1.12 Georgia,serif;margin:0 0 14px;letter-spacing:-1.5px}
    .atlas-hero p {color:#586650;max-width:650px;font-size:16px;margin:0}
    .atlas-chip {display:inline-block;padding:5px 10px;border:1px solid #c5cfa3;background:#e9efcf;color:#334b28;font-size:11px;letter-spacing:.5px;margin:14px 8px 0 0;border-radius:3px}
    [data-testid="stForm"] {border:1px solid #c5cbb7;background:#fffef8;border-radius:8px;padding:24px}
    [data-testid="stTextInput"] input,[data-testid="stTextArea"] textarea {background:#fffef8;color:#24362d}
    [data-testid="stFormSubmitButton"] button {background:#24523d;color:white;border:1px solid #24523d;border-radius:5px;min-height:44px}
    [data-testid="stFormSubmitButton"] button:hover {background:#173c2b;color:white;border-color:#173c2b}
    [data-testid="stMetric"] {background:#e9efcf;border:1px solid #c5cbb7;padding:14px;border-radius:5px}
    [data-testid="stExpander"] {background:#fffef8;border-radius:5px}
    a {color:#24523d}
    @media(max-width:640px){.atlas-hero h1{font-size:35px}.block-container{padding-top:2rem}[data-testid="stForm"]{padding:16px}}
    </style>''', unsafe_allow_html=True)
    with st.sidebar:
        st.markdown('<div class="atlas-brand">ATLAS<span>✳</span></div>', unsafe_allow_html=True)
        st.caption('PROVIDER PERFORMANCE / LIVE EXPLORER')
        st.divider()
        st.markdown('### A smaller dataset.\nA closer look.')
        st.write('Ask about spending, utilization and provider attribution in a deterministic synthetic fixture.')
        st.metric('Synthetic members', '1,000')
        st.caption('Sample 1 only · 2009–2010')
        st.markdown('[← Explore the full dashboard](https://karthikeyansett1-medicare-provider-performance.static.hf.space/index.html)')
        st.markdown('[Project & methodology ↗](https://github.com/karthikeyansett1/medicare-claims)')
        st.divider()
        st.markdown('**Private reviewer access**')
        st.caption('Ask the project owner for an access code. Never enter an API key or database password here.')
        with st.expander('Usage allowance'):
            st.write('One shared $5 lifetime API allowance. Conservative reservations are never refunded, so a few questions may exhaust it. Hosting and database free-tier quotas also apply.')
    st.markdown('''<div class="atlas-hero"><div class="atlas-label">CLAIMS EXPLORER / LIVE AI DEMO</div>
    <h1>Start with a question.<br>Follow the evidence.</h1>
    <p>Explore synthetic Medicare claims in plain English, then inspect the SQL and data behind each answer.</p>
    <span class="atlas-chip">1,000-MEMBER FIXTURE</span><span class="atlas-chip">READ-ONLY QUERIES</span><span class="atlas-chip">ACCESS CODE REQUIRED</span></div>''', unsafe_allow_html=True)
    try:
        values=dict(os.environ)
        try:values.update(dict(st.secrets))
        except FileNotFoundError:pass
        cfg=Config.from_mapping(values)
    except Exception:
        st.error('The explorer is awaiting its private configuration. Please contact the project owner.');st.stop()
    left,right=st.columns([2.2,1],gap='large')
    with left:
        st.subheader('Ask the data')
        # Authenticate on every request; the code is not retained after submit.
        with st.form('live_question',clear_on_submit=True):
            question=st.text_area('Your question',placeholder='What is the average medical PMPM for 2009?',max_chars=1500,height=120)
            year_col,method_col=st.columns(2)
            with year_col:year=st.selectbox('Performance year',[2009,2010])
            with method_col:method=st.selectbox('Attribution method',['A_visits','B_allowed'],format_func=lambda v:{'A_visits':'A · Visit plurality','B_allowed':'B · Allowed cost'}[v])
            code=st.text_input('Private access code',type='password',help='Use the code shared by the project owner. It clears after each submission.')
            submitted=st.form_submit_button('Explore answer ↗',width='stretch')
            st.caption('Submitting uses the shared API allowance. Browsing this page does not.')
    with right:
        st.subheader('Try a starting point')
        st.markdown('**Spending**\n\nWhat is the average medical PMPM for 2009?\n\n**Provider panels**\n\nWhich providers have the highest PMPM among panels with at least 20 members?\n\n**Conditions**\n\nWhich conditions account for the most inpatient spending?')
        st.divider()
        st.caption('Use synthetic data questions only. Do not enter patient information. Results describe this fixture, not the full CMS samples or clinical quality.')
    if submitted:
        st.session_state.pop('live_result',None)
        if not authorized(code,cfg):st.error('Access code is incorrect. Use the private code shared by the project owner.');return
        if not question.strip():st.warning('Enter a question to explore.');return
        try:
            with st.spinner('Checking the fixture, querying the data and preparing your answer…'):
                st.session_state.live_result=LiveAgent(cfg,code).ask(question,year=year,method=method)
        except (LiveUnavailable,AssistantError) as error:st.error(str(error))
        except Exception:st.error('Assistant unavailable. No further calls were sent.')
    if 'live_result' in st.session_state:
        result=st.session_state.live_result
        st.divider()
        st.subheader('What the data says')
        st.markdown(result['answer'])
        with st.expander('Scope & assumptions',expanded=True):
            for assumption in result['assumptions']:st.markdown('- '+assumption)
        if result['sql']:
            data_tab,sql_tab=st.tabs(['Result table','Query SQL'])
            with data_tab:st.dataframe(result['rows'],width='stretch',hide_index=True)
            with sql_tab:st.code(result['sql'],language='sql')
    st.divider()
    st.caption('ATLAS / '+SCOPE+' Medical payments exclude prescription gross costs. Descriptive research demonstration.')
