from pathlib import Path
from types import SimpleNamespace
import pytest
from assistant.live_app import Config,authorized,LiveAgent,fixture_clarification,verify_privileges
from assistant.live_budget import LiveUnavailable


def config():
    return Config.from_mapping({'LIVE_ACCESS_CODE':'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-',
      'LIVE_OPENAI_API_KEY':'unit-test-key','LIVE_QUERY_DATABASE_URL':'postgresql://medicare_demo_ro:pw@host/db?sslmode=verify-full',
      'LIVE_BUDGET_DATABASE_URL':'postgresql://medicare_live_budget:pw@host/db?sslmode=verify-full'})


def test_config_fail_closed_and_no_secret_repr():
    with pytest.raises(LiveUnavailable):Config.from_mapping({})
    cfg=config();assert 'unit-test-key' not in repr(cfg) and 'pw@' not in repr(cfg)
    assert authorized(cfg.access_code,cfg) and not authorized('wrong',cfg)


def test_auth_precedes_any_initialization():
    touches=[]
    with pytest.raises(LiveUnavailable):LiveAgent(config(),'bad',client_factory=lambda **kw:touches.append('api'),verify=lambda cfg:touches.append('db'))
    assert touches==[]


@pytest.mark.parametrize('text',['sample 2','Sample two','sample #2','second sample','2nd sample','samples 1 and 2','Ｓａｍｐｌｅ ２','both samples','all CMS samples','full dataset'])
def test_unsupported_scope_clarifies_without_call(text):
    assert fixture_clarification(text)
    agent=LiveAgent.__new__(LiveAgent)
    assert agent.ask(text)['clarification']


def test_query_role_cannot_execute_budget_functions():
    class Conn:
        def execute(self,query):
            if 'pg_class' in query:return SimpleNamespace(fetchall=lambda:[])
            if 'has_function_privilege' in query:return SimpleNamespace(fetchall=lambda:[('reserve',True),('status',True)])
            return SimpleNamespace(fetchone=lambda:(False,))
    with pytest.raises(ValueError):verify_privileges(Conn(),True)


def test_budget_role_cannot_read_or_write_tables():
    class Conn:
        def execute(self,query):
            if 'pg_class' in query:return SimpleNamespace(fetchall=lambda:[('live_budget.campaign',False,True)])
            return SimpleNamespace(fetchone=lambda:(False,))
    with pytest.raises(ValueError):verify_privileges(Conn(),False)


def test_sql_bootstrap_has_no_reset_and_fixed_cap():
    sql=Path('deployment/live/bootstrap.sql').read_text()
    assert 'FOR UPDATE' in sql and 'cap_microdollars=5000000' in sql
    assert 'SECURITY DEFINER SET search_path=pg_catalog,live_budget' in sql
    assert 'ON CONFLICT' not in '\n'.join(l for l in sql.splitlines() if not l.startswith('--'))
    assert 'GRANT EXECUTE' in sql and 'REVOKE ALL ON ALL TABLES' in sql


def test_verified_tls_and_roles_required():
    cfg=config()
    values={'LIVE_ACCESS_CODE':cfg.access_code,'LIVE_OPENAI_API_KEY':cfg.api_key,
            'LIVE_QUERY_DATABASE_URL':cfg.query_dsn,'LIVE_BUDGET_DATABASE_URL':cfg.budget_dsn}
    for field,value in [('LIVE_QUERY_DATABASE_URL',cfg.query_dsn.replace('medicare_demo_ro','admin')),
                        ('LIVE_BUDGET_DATABASE_URL',cfg.budget_dsn.replace('verify-full','require')),
                        ('LIVE_ACCESS_CODE','a'*48)]:
        changed={**values,field:value}
        with pytest.raises(LiveUnavailable):Config.from_mapping(changed)


def test_existing_agent_executor_injection_is_late_bound(monkeypatch):
    import json
    from assistant.sql_agent import Agent
    agent=Agent.__new__(Agent);calls=[]
    agent.execute_query=lambda sql:(calls.append(sql) or ('SELECT checked',[{'value':7}]))
    replies=iter([json.dumps({'assumptions':[],'sql':'SELECT proposed','clarification':''}),'Seven'])
    agent._call=lambda *args,**kwargs:next(replies)
    monkeypatch.setattr('assistant.sql_agent.log_event',lambda data:None)
    result=agent.ask('A unit question')
    assert calls==['SELECT proposed'] and result['rows']==[{'value':7}]
