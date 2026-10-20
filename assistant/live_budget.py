"""Independent public-live guard. No evaluator imports, refunds or local counters."""
from decimal import Decimal, ROUND_CEILING
import json
from types import SimpleNamespace
import psycopg
import certifi

MODEL = 'gpt-6-astra'
CAMPAIGN = 'sample1-fixture-live-v1'
CAP_MICRODOLLARS = 5_000_000


class LiveUnavailable(RuntimeError):
    pass


def reservation(kwargs):
    allowed = {'model','input','max_output_tokens','store','text','service_tier','reasoning'}
    if set(kwargs)-allowed or kwargs.get('model') != MODEL or kwargs.get('service_tier') != 'default':
        raise LiveUnavailable('Unreviewed request configuration.')
    if kwargs.get('reasoning') != {'effort':'low'} or kwargs.get('store') is not False:
        raise LiveUnavailable('Unreviewed request configuration.')
    output = kwargs.get('max_output_tokens')
    if type(output) is not int or not 1 <= output <= 3000:
        raise LiveUnavailable('Invalid output limit.')
    messages = kwargs.get('input')
    if not isinstance(messages,list) or any(not isinstance(m,dict) or set(m)!={'role','content'} or m['role'] not in ('system','user','assistant') or not isinstance(m['content'],str) for m in messages):
        raise LiveUnavailable('Only self-contained text requests are allowed.')
    bound = len(json.dumps(kwargs,ensure_ascii=False).encode('utf-8')) + 8192
    if bound > 70000:
        raise LiveUnavailable('Request exceeds the reviewed input limit.')
    # USD/M tokens equals microdollars/token. Use the higher cache-write rate.
    microdollars = int((Decimal(bound)*Decimal('12.5')+Decimal(output)*50).to_integral_value(rounding=ROUND_CEILING))
    return bound, microdollars


class PostgresBudget:
    def __init__(self, dsn, connect=psycopg.connect):
        self._dsn, self._connect = dsn, connect

    def reserve(self, input_bound, output_bound, microdollars):
        try:
            # Commit must finish before this method returns and before API dispatch.
            with self._connect(self._dsn, connect_timeout=10, sslmode='verify-full', sslrootcert=certifi.where()) as conn:
                conn.execute("SET LOCAL statement_timeout='10s'")
                conn.execute("SET LOCAL lock_timeout='5s'")
                row=conn.execute('SELECT live_budget.reserve(%s,%s,%s,%s)',
                                 (CAMPAIGN,input_bound,output_bound,microdollars)).fetchone()
                if not row or not isinstance(row[0],int) or row[0] <= 0:
                    raise LiveUnavailable('Budget reservation unavailable.')
            return row[0]
        except Exception:
            # DB text can include DSNs; expose no exception details.
            raise LiveUnavailable('Live allowance unavailable or exhausted. No API call was sent.') from None


class BudgetedClient:
    def __init__(self, client, budget):
        self._client,self._budget=client,budget
        self.responses=SimpleNamespace(create=self.create)

    def create(self, **kwargs):
        bound, cost=reservation(kwargs)
        self._budget.reserve(bound,kwargs['max_output_tokens'],cost)
        # All reservations, including timeouts, remain spent permanently.
        return self._client.responses.create(**kwargs)
