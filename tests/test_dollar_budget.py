from decimal import Decimal
import pytest
from assistant.dollar_budget import DollarLedger, usage_cost
from assistant.sql_agent import AssistantError


def usage(i=100,o=20,c=30,w=50):
    return {'input_tokens':i,'output_tokens':o,'input_tokens_details':{'cached_tokens':c,'cache_write_tokens':w}}


def test_exact_cache_prices_and_reasoning_in_output():
    assert usage_cost(usage()) == Decimal('0.001855')


@pytest.mark.parametrize('u',[usage(c=101),usage(w=-1),usage(i=-1),usage(o=True),usage(c=None)])
def test_invalid_usage_never_releases_reservation(tmp_path,u):
    ledger=DollarLedger(tmp_path/'ledger.db')
    identifier=ledger.reserve(1,'test')
    with pytest.raises((ValueError,AssistantError)):
        ledger.settle(identifier,u,1000,3000)
    assert ledger.summary()['charged_or_reserved_usd']=='1'


def test_settlement_frees_only_validated_unused_allowance(tmp_path):
    ledger=DollarLedger(tmp_path/'ledger.db')
    identifier=ledger.reserve(19,'a')
    with pytest.raises(AssistantError): ledger.reserve(2,'b')
    ledger.settle(identifier,usage(),1000,3000)
    ledger.reserve(19,'b')
    assert ledger.summary()['charged_or_reserved_usd']=='19.001855'
    with pytest.raises(AssistantError): ledger.settle(identifier,usage(),1000,3000)


def test_separate_connections_share_cap_and_unknown_is_retained(tmp_path):
    a=DollarLedger(tmp_path/'ledger.db'); b=DollarLedger(tmp_path/'ledger.db')
    a.reserve(10,'a'); b.reserve(10,'b')
    with pytest.raises(AssistantError): a.reserve(.01,'a')
    assert b.summary()['unknown_usage_calls']==2


def test_prior_seed_is_idempotent_and_nonempty_unseeded_fails_closed(tmp_path):
    import json
    evidence=tmp_path/'evidence.json'
    evidence.write_text(json.dumps({'calls':[{'usage':usage(),'reserved_usd':1}]}))
    a=DollarLedger(tmp_path/'a.db'); a.reserve(1,'evaluation')
    with pytest.raises(AssistantError,match='lacks matching'):
        a.seed_smoke(evidence)
    b=DollarLedger(tmp_path/'b.db'); b.seed_smoke(evidence); b.seed_smoke(evidence)
    assert b.summary()['calls']==1
    evidence.write_text(json.dumps({'calls':[]}))
    with pytest.raises(AssistantError,match='changed'):
        b.seed_smoke(evidence)
