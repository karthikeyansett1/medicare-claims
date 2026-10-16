"""Unit fixtures only: fake outputs are not AI accuracy evidence."""
from datetime import date
from decimal import Decimal
import json
import pytest
from eval import run_eval as ev


def test_comparator_shapes_types_duplicates_order():
    assert ev.compare_rows([{'a': 1}, {'a': 2}], [{'x': 2}, {'x': 1}])
    assert not ev.compare_rows([(1,), (1,)], [(1,), (2,)])
    assert not ev.compare_rows([(1,2)], [(1,)])
    assert not ev.compare_rows([(True,)], [(1,)])
    assert not ev.compare_rows([(None,)], [('None',)])
    assert ev.compare_rows([(date(2009,1,1),)], [(date(2009,1,1),)])
    assert not ev.compare_rows([(date(2009,1,1),)], [('2009-01-01',)])
    assert not ev.compare_rows([(1,), (2,)], [(2,), (1,)], ordered=True)
    assert ev.compare_rows([], [])


def test_tolerance_matching_not_rounding_or_greedy():
    assert ev.compare_rows([(Decimal('1.0049'),)], [(1.0051,)], {'abs': .001})
    assert ev.compare_rows([(1000000,)], [(1000001,)], {'rel': .000002})
    assert not ev.compare_rows([(0,)], [(0.1,)], {'rel': .01})
    assert ev.compare_rows([(0.1,), (0,)], [(0,), (.2,)], {'abs': .11})
    assert not ev.compare_rows([(float('nan'),)], [(float('nan'),)])
    assert not ev.compare_rows([(float('inf'),)], [(float('inf'),)])
    with pytest.raises(ValueError):
        ev.compare_rows([], [], {'abs': -1})


def test_live_quota_stops_without_score_and_keeps_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(ev, 'execute', lambda sql: (sql, [(1,)]))
    calls = []
    class UnitOnlyAgent:
        model = 'unit-only'
        usage = []
        def __init__(self, *args): pass
        def ask(self, question, **defaults):
            calls.append(question)
            raise RuntimeError('insufficient_quota')
    qs = [{'id':str(i), 'question':'unit only', 'gold_sql':'secret gold', 'category':'simple_lookup'} for i in range(3)]
    report = ev.run_live(qs, tmp_path, {'model':'unit-only'}, 'unit-only', 1, 3, 10000, agent_factory=UnitOnlyAgent)
    assert len(calls)==1
    assert report['accuracy'] is None and not report['complete']
    row = json.loads((tmp_path/'results.jsonl').read_text())
    assert row['error']=='RuntimeError:insufficient_quota'
    assert row['failure_type'] in ev.TAXONOMY
    assert row['input_tokens'] is None
    assert 'secret gold' not in (tmp_path/'results.jsonl').read_text()
    with pytest.raises(ValueError, match='identity'):
        ev.run_live(qs, tmp_path, {'model':'changed'}, 'unit-only', 1, 3, 10000, True, UnitOnlyAgent)


def test_ambiguous_requires_text_and_no_sql(tmp_path):
    class UnitOnlyAgent:
        model = 'unit-only'
        usage = []
        def __init__(self, *args): pass
        def ask(self, question, **defaults):
            assert question == 'unit fixture question'
            return {'sql':'', 'answer':'', 'clarification':True, 'rows':[]}
    qs=[{'id':'a', 'question':'unit fixture question', 'gold_sql':'', 'category':'ambiguous'}]
    ev.run_live(qs, tmp_path, {'model':'unit-only'}, 'unit-only', 1, 3, 10000, agent_factory=UnitOnlyAgent)
    row=json.loads((tmp_path/'results.jsonl').read_text())
    assert not row['pass'] and row['failure_type']==ev.TAXONOMY[7]


def test_eval_budget_reserves_before_call(monkeypatch):
    monkeypatch.setattr(ev.Agent, '__init__', lambda self: None)
    calls=[]
    monkeypatch.setattr(ev.Agent, '_call', lambda *args: calls.append('unit-only'))
    state={'calls_reserved':0,'tokens_reserved':0}
    agent=ev.BoundedAgent(1,100000,state,lambda: calls.append('persist'))
    agent._call([])
    assert calls==['persist','unit-only']
    with pytest.raises(ev.EvaluationBudget): agent._call([])
    assert state['calls_reserved']==1


def test_question_validation_contract(tmp_path, monkeypatch):
    import yaml
    monkeypatch.setattr(ev, 'validate_sql', lambda sql: sql)
    qs=[]
    for category, count in ev.CATEGORIES.items():
        for i in range(count):
            qs.append({'id':f'{category}{i}', 'question':f'Unit fixture {category} {i}',
                       'category':category, 'gold_sql':'' if category=='ambiguous' else 'SELECT 1'})
    path=tmp_path/'questions.yaml'
    path.write_text(yaml.safe_dump({'questions':qs}))
    assert len(ev.load_questions(path))==50
    qs[-1]['gold_sql']='SELECT 1'
    path.write_text(yaml.safe_dump({'questions':qs}))
    with pytest.raises(ValueError, match='Ambiguous'):
        ev.load_questions(path)
    qs[-1]['gold_sql']=''
    qs[-1]['id']=qs[0]['id']
    path.write_text(yaml.safe_dump({'questions':qs}))
    with pytest.raises(ValueError, match='unique'):
        ev.load_questions(path)


def test_unknown_usage_never_becomes_zero_or_partial_total():
    assert ev.usage_total([], 'input_tokens') is None
    assert ev.usage_total([{'input_tokens':10},{'input_tokens':None}], 'input_tokens') is None
    assert ev.usage_total([{'input_tokens':0}], 'input_tokens') == 0
    assert ev.usage_total([{'input_tokens':10},{'input_tokens':5}], 'input_tokens') == 15


def test_successful_plan_then_explanation_failure_has_unknown_totals(tmp_path, monkeypatch):
    monkeypatch.setattr(ev, 'execute', lambda sql:(sql,[(1,)]))
    class TwoCallAgent:
        model='unit-only'
        def __init__(self,*args): self.usage=[]
        def ask(self, question, **kwargs):
            self.usage.append({'input_tokens':50,'output_tokens':10})
            raise ev.AssistantError('OpenAI request failed: APITimeoutError')
    questions=[{'id':'test','question':'unit question','gold_sql':'SELECT 1','category':'simple_lookup'}]
    ev.run_live(questions,tmp_path,{'model':'unit-only'},'unit-only',1,3,10000,agent_factory=TwoCallAgent)
    result=json.loads((tmp_path/'results.jsonl').read_text())
    assert result['input_tokens'] is None and result['output_tokens'] is None
    assert result['known_input_tokens']==50 and result['known_output_tokens']==10
    assert not result['token_totals_complete']


def test_live_preflight_cannot_reset_cap_with_fresh_ledger(tmp_path, monkeypatch):
    monkeypatch.setattr(ev,'ROOT',tmp_path)
    with pytest.raises(ValueError,match='existing authorized'):
        ev.prepare_owner_ledger(tmp_path/'fresh.db')
    expected=tmp_path/'eval/results/funded_2026-10-14.sqlite3'
    with pytest.raises(ValueError,match='existing authorized'):
        ev.prepare_owner_ledger(expected)
    assert not expected.exists()
