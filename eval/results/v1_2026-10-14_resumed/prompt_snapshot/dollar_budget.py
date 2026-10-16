"""Owner-run dollar ledger. Unknown usage always retains its full reservation."""
import json
import sqlite3
import time
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from assistant.funded_smoke import request_bound
from assistant.sql_agent import Agent, AssistantError
from assistant.budget import BudgetError

CAP = Decimal('20')


def usage_cost(usage):
    """Standard Astra pricing, including cache writes; reject inconsistent usage."""
    i, o = usage['input_tokens'], usage['output_tokens']
    details = usage.get('input_tokens_details') or {}
    c, w = details.get('cached_tokens'), details.get('cache_write_tokens')
    # Missing cache accounting is uncertain: keep the original reservation.
    if any(type(x) is not int or x < 0 for x in [i, o]):
        raise ValueError('Invalid usage')
    if c is None or w is None:
        raise ValueError('Missing cache usage')
    if any(type(x) is not int or x < 0 for x in [c, w]) or c+w > i:
        raise ValueError('Invalid cache usage')
    return (Decimal(i-c-w)*10+Decimal(c)+Decimal(w)*Decimal('12.5')+Decimal(o)*50)/1_000_000


class DollarLedger:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS calls (id INTEGER PRIMARY KEY, created REAL, run TEXT, reservation TEXT, charged TEXT, status TEXT, usage TEXT)')
        self.path.chmod(0o600)

    def db(self):
        return sqlite3.connect(self.path, timeout=10)

    def reserve(self, amount, run):
        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValueError('Positive reservation required')
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            total = sum((Decimal(r[0]) for r in db.execute('SELECT charged FROM calls')), Decimal(0))
            if total+amount > CAP:
                raise AssistantError('Shared $20 dollar cap reached before dispatch.')
            cur=db.execute('INSERT INTO calls (created,run,reservation,charged,status) VALUES (?,?,?,?,?)',
                           (time.time(),run,str(amount),str(amount),'unknown_reserved'))
            return cur.lastrowid

    def settle(self, identifier, usage, input_bound, output_bound):
        amount = usage_cost(usage)
        if usage['input_tokens'] > input_bound or usage['output_tokens'] > output_bound:
            raise AssistantError('Provider usage exceeded reservation bounds; stop.')
        with self.db() as db:
            row=db.execute('SELECT reservation,status FROM calls WHERE id=?',(identifier,)).fetchone()
            if not row or row[1] != 'unknown_reserved' or amount > Decimal(row[0]):
                raise AssistantError('Invalid usage settlement; reservation retained.')
            db.execute('UPDATE calls SET charged=?,status=?,usage=? WHERE id=?',
                       (str(amount),'usage_settled',json.dumps(usage),identifier))

    def seed_smoke(self, evidence):
        data=json.loads(Path(evidence).read_text())
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT COUNT(*) FROM calls').fetchone()[0]:
                return
            for call in data['calls']:
                usage=call.get('usage')
                amount=usage_cost(usage) if usage else Decimal(str(call['reserved_usd']))
                db.execute('INSERT INTO calls (created,run,reservation,charged,status,usage) VALUES (?,?,?,?,?,?)',
                           (time.time(),'prior_smoke',str(call['reserved_usd']),str(amount),'usage_settled' if usage else 'unknown_reserved',json.dumps(usage)))

    def summary(self):
        with self.db() as db:
            rows=list(db.execute('SELECT run,reservation,charged,status,usage FROM calls'))
        return {'limit_usd':str(CAP),'charged_or_reserved_usd':str(sum((Decimal(r[2]) for r in rows),Decimal(0))),
                'calls':len(rows),'unknown_usage_calls':sum(r[3]=='unknown_reserved' for r in rows),
                'entries':[dict(zip(['run','reservation','charged','status','usage'],r)) for r in rows]}


class DollarClient:
    def __init__(self, client, ledger, run):
        self.client,self.ledger,self.run=client,ledger,run
        self.responses=SimpleNamespace(create=self.create)

    def create(self, **kwargs):
        kwargs.update(service_tier='default', reasoning={'effort':'low'})
        bound,amount=request_bound(kwargs)
        identifier=self.ledger.reserve(amount,self.run)
        response=self.client.responses.create(**kwargs)
        if response.model != 'gpt-6-astra' and not response.model.startswith('gpt-6-astra-'):
            raise AssistantError('Unexpected response model; retain reservation and stop.')
        if getattr(response,'service_tier',None) != 'default':
            raise AssistantError('Unverified response tier; retain reservation and stop.')
        if response.usage:
            self.ledger.settle(identifier,response.usage.model_dump(),bound,kwargs['max_output_tokens'])
        else:
            raise AssistantError('Unknown usage; retain reservation and stop.')
        return response


class PacedOwnerAgent(Agent):
    """Owner-only runner waits for existing server minute allowance; no API retries."""
    def _call(self, messages, structured=False):
        for attempt in range(7):
            try:
                return super()._call(messages,structured)
            except BudgetError as error:
                if 'minute' not in str(error) or attempt == 6:
                    raise
                time.sleep(10.2)
