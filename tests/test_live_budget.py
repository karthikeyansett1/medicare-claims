import threading
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from decimal import Decimal
import pytest
from assistant.live_budget import reservation,BudgetedClient,PostgresBudget,LiveUnavailable


def request():
    return dict(model='gpt-6-astra',input=[{'role':'user','content':'hello'}],max_output_tokens=3000,store=False,service_tier='default',reasoning={'effort':'low'})


@pytest.mark.parametrize('change',[{'model':'other'},{'service_tier':'fast'},{'max_output_tokens':True},{'max_output_tokens':3001},{'tools':[]},{'previous_response_id':'x'},{'input':[{'role':'user','content':[{'type':'input_image'}]}]},{'input':[{'role':'user','content':'x'*70000}]}])
def test_unpriced_requests_blocked(change):
    kwargs=request();kwargs.update(change)
    with pytest.raises(LiveUnavailable):reservation(kwargs)


def test_schema_and_multibyte_content_counted():
    a=request();before,_=reservation(a);a['text']={'format':{'schema':'é'*100}}
    after,amount=reservation(a)
    assert after>=before+200
    assert amount>=Decimal(after)*Decimal('12.5')+150000


def test_commit_must_finish_before_dispatch_and_failure_stops_api():
    events=[]
    class Conn:
        def __enter__(self):return self
        def execute(self,sql,params=None):events.append('sql');return SimpleNamespace(fetchone=lambda:(1,))
        def __exit__(self,*args):events.append('commit');raise OSError('secret DSN must not escape')
    budget=PostgresBudget('secret',connect=lambda *a,**kw:Conn())
    client=BudgetedClient(SimpleNamespace(responses=SimpleNamespace(create=lambda **kw:events.append('api'))),budget)
    with pytest.raises(LiveUnavailable,match='No API call') as error:client.responses.create(**request())
    assert 'api' not in events and 'secret' not in str(error.value)


def test_nonrefundable_failure_and_shared_atomic_mock_limit():
    # Models a shared atomic store to test wrapper ordering, not PostgreSQL locking.
    class Ledger:
        def __init__(self):self.spent=0;self.lock=threading.Lock();self.calls=0
        def reserve(self,i,o,amount):
            with self.lock:
                if self.spent+amount>5000000:raise LiveUnavailable('cap')
                self.spent+=amount;self.calls+=1
    ledger=Ledger();attempts=[]
    def fail(**kw):attempts.append(1);raise TimeoutError()
    client=BudgetedClient(SimpleNamespace(responses=SimpleNamespace(create=fail)),ledger)
    def send(_):
        try:client.responses.create(**request())
        except (TimeoutError,LiveUnavailable):pass
    with ThreadPoolExecutor(max_workers=8) as pool:list(pool.map(send,range(40)))
    _,amount=reservation(request())
    assert ledger.spent==len(attempts)*amount<=5000000
    assert ledger.spent+amount>5000000 and ledger.calls==len(attempts)


def test_budget_connection_uses_explicit_verified_ca_bundle():
    import certifi
    captured={}
    def connect(dsn,**kwargs):
        captured.update(kwargs)
        raise OSError('offline fixture')
    with pytest.raises(LiveUnavailable):PostgresBudget('dsn',connect=connect).reserve(9000,3000,262500)
    assert captured['sslmode']=='verify-full' and captured['sslrootcert']==certifi.where()
    assert 'options' not in captured
