from types import SimpleNamespace
import pytest
from assistant.funded_smoke import Meter, request_bound
from assistant.sql_agent import AssistantError


def request():
    return dict(model='gpt-6-astra', service_tier='default', max_output_tokens=3000, input='hello')


def test_bound_includes_schema_and_multibyte_bytes():
    a = request()
    base, _ = request_bound(a)
    a['text'] = {'schema': 'é'*100}
    large, price = request_bound(a)
    assert large >= base + 200
    assert price == (large*12.5+3000*50)/1_000_000


def test_budget_blocks_before_dispatch_and_retains_unknown():
    sent = []
    def fail(**kwargs):
        sent.append(kwargs)
        raise RuntimeError('network lost')
    report = {'calls': []}
    meter = Meter(SimpleNamespace(responses=SimpleNamespace(create=fail)), report, lambda: None)
    with pytest.raises(RuntimeError):
        meter.create(**request())
    assert len(sent)==1 and report['calls'][0]['usage'] is None
    report['calls'].append({'reserved_usd': 4.9})
    with pytest.raises(AssistantError, match='before dispatch'):
        meter.create(**request())
    assert len(sent)==1


@pytest.mark.parametrize('change', [{'model':'other'}, {'service_tier':'fast'}, {'max_output_tokens':3001}, {'tools':[{}]}, {'input':'x'*70000}])
def test_unreviewed_costs_rejected(change):
    kwargs=request()
    kwargs.update(change)
    with pytest.raises(ValueError):
        request_bound(kwargs)


def test_cache_write_cost_is_accounted_at_higher_rate():
    usage = SimpleNamespace(input_tokens=100, output_tokens=20,
        input_tokens_details=SimpleNamespace(cached_tokens=30, cache_write_tokens=50),
        model_dump=lambda: {'input_tokens':100})
    response = SimpleNamespace(status='completed', model='gpt-6-astra', service_tier='default', usage=usage)
    report = {'calls': []}
    client = SimpleNamespace(responses=SimpleNamespace(create=lambda **kwargs: response))
    meter = Meter(client, report, lambda: None)
    meter.create(**request())
    assert report['calls'][0]['standard_usage_estimate_usd'] == (20*10+30+50*12.5+20*50)/1_000_000
