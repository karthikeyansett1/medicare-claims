"""Export credential-free, usage-based accounting; never treat unknown costs as zero."""
import json
from collections import defaultdict
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path
from assistant.dollar_budget import DollarLedger
ROOT=Path(__file__).resolve().parents[1]

def main():
    ledger=DollarLedger(ROOT/'eval/results/funded_2026-10-14.sqlite3').summary()
    groups=defaultdict(lambda:{'calls':0,'known_usage_cost_usd':Decimal(0),'unknown_reserved_usd':Decimal(0),'input_tokens':0,'output_tokens':0,'cached_input_tokens':0,'cache_write_tokens':0,'reasoning_output_tokens':0,'unknown_usage_calls':0})
    for entry in ledger['entries']:
        g=groups[entry['run']];g['calls']+=1
        if entry['status']=='unknown_reserved':
            g['unknown_reserved_usd']+=Decimal(entry['charged']);g['unknown_usage_calls']+=1
        else:
            g['known_usage_cost_usd']+=Decimal(entry['charged']);u=json.loads(entry['usage'])
            g['input_tokens']+=u['input_tokens'];g['output_tokens']+=u['output_tokens']
            g['cached_input_tokens']+=u['input_tokens_details']['cached_tokens'];g['cache_write_tokens']+=u['input_tokens_details']['cache_write_tokens']
            g['reasoning_output_tokens']+=(u.get('output_tokens_details') or {}).get('reasoning_tokens',0)
    report={'exported_at_utc':datetime.now(timezone.utc).isoformat(),'limit_usd':ledger['limit_usd'],'known_usage_cost_usd':str(sum(g['known_usage_cost_usd'] for g in groups.values())),'unknown_reserved_usd':str(sum(g['unknown_reserved_usd'] for g in groups.values())),'charged_or_reserved_usd':ledger['charged_or_reserved_usd'],'unknown_usage_calls':ledger['unknown_usage_calls'],'groups':dict(groups),'rates_usd_per_million':{'input':10,'cached_read':1,'cache_write':12.5,'output_including_reasoning':50},'pricing_source':'https://developers.openai.com/api/docs/models/gpt-6-astra','pricing_verified_date':'2026-10-14','limitations':'Usage-based estimate, not an invoice or live account balance. Historical pre-funding 429 attempts lacked usage and are outside this newly funded run; their charge is unknown. Unknown funded timeout reservations remain fully charged against the cap. No other account activity is measured.'}
    (ROOT/'eval/results/cost_evidence_2026-10-15.json').write_text(json.dumps(report,indent=2,default=str)+'\n')
    print(json.dumps({k:report[k] for k in ['known_usage_cost_usd','unknown_reserved_usd','charged_or_reserved_usd']}))

if __name__=='__main__':main()
