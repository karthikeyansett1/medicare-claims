import json
from types import SimpleNamespace
import pytest
from assistant import sql_agent
from assistant.budget import reserve, BudgetError
from assistant.guardrails import GuardrailError


def response(text):
    return SimpleNamespace(output_text=text,status='completed',model='test-model',usage=SimpleNamespace(input_tokens=10,output_tokens=5))


def plan(sql='', clarification=''):
    return json.dumps({'assumptions':['Sample 1, 2009, A_visits; medical paid excludes Rx.'],'sql':sql,'clarification':clarification})


def agent(monkeypatch,replies):
    seen=[]
    def create(**kwargs):
        seen.append(kwargs)
        return response(replies.pop(0))
    monkeypatch.setattr(sql_agent,'reserve',lambda *a:None)
    monkeypatch.setattr(sql_agent,'log_event',lambda *a:None)
    return sql_agent.Agent(SimpleNamespace(responses=SimpleNamespace(create=create))),seen


def test_clarification_never_queries(monkeypatch):
    a,seen=agent(monkeypatch,[plan(clarification='Which quality measure?')])
    monkeypatch.setattr(sql_agent,'execute',lambda s:pytest.fail('Clarification ran SQL'))
    assert a.ask('Who is best?')['clarification']
    assert len(seen)==1
    assert seen[0]['store'] is False


def test_one_repair_then_grounded_answer(monkeypatch):
    a,seen=agent(monkeypatch,[plan('bad'),plan('good'),'Based on the supplied rows, 3 members.'])
    queries=[]
    def execute(sql):
        queries.append(sql)
        if sql=='bad': raise GuardrailError('Unknown column')
        return 'SELECT COUNT(*) FROM gold.dim_member_year LIMIT 500',[{'count':3}]
    monkeypatch.setattr(sql_agent,'execute',execute)
    result=a.ask('How many members?')
    assert queries==['bad','good']
    assert len(seen)==3
    assert result['rows']==[{'count':3}]
    assert len(result['usage'])==3
    assert 'count' in seen[-1]['input'][-1]['content']


def test_second_failure_stops(monkeypatch):
    a,seen=agent(monkeypatch,[plan('bad'),plan('bad')])
    def fail(sql): raise GuardrailError('Denied')
    monkeypatch.setattr(sql_agent,'execute',fail)
    with pytest.raises(sql_agent.AssistantError,match='after one repair'): a.ask('Count members')
    assert len(seen)==2


def test_persistent_server_budget(tmp_path,monkeypatch):
    monkeypatch.setenv('ASSISTANT_CALLS_PER_DAY','2')
    monkeypatch.setenv('ASSISTANT_TOKEN_BUDGET_PER_DAY','100')
    path=tmp_path/'budget.sqlite3'
    reserve(20,20,path)
    reserve(20,20,path)
    with pytest.raises(BudgetError): reserve(1,1,path)


def test_database_fetch_deadline(monkeypatch):
    from assistant import database
    times=iter([0,21])
    monkeypatch.setattr(database.time,'monotonic',lambda:next(times))
    class Cursor:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def execute(self,*args): pass
        def fetchone(self): pytest.fail('Expired deadline must stop fetch')
    class Conn(Cursor):
        def cursor(self,**kwargs): return Cursor()
    monkeypatch.setattr(database,'connect',lambda:Conn())
    with pytest.raises(GuardrailError,match='deadline'):
        database.execute('SELECT y.year FROM gold.dim_member_year y')
