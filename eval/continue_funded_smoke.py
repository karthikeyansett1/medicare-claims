"""Complete the original public few-shot smoke under the shared owner $20 ledger."""
import json
import os
from pathlib import Path
import yaml
from assistant.dollar_budget import DollarLedger,DollarClient,PacedOwnerAgent
from assistant.sql_agent import HERE,AssistantError
from assistant.database import execute
from eval.run_eval import compare_rows

ROOT=Path(__file__).resolve().parents[1]
LEDGER=ROOT/'eval/results/funded_2026-10-14.sqlite3'
OUTPUT=ROOT/'eval/results/smoke_2026-10-14_complete.json'

def main():
    os.environ['ASSISTANT_CALLS_PER_DAY']='1000'
    os.environ['ASSISTANT_TOKEN_BUDGET_PER_DAY']='100000000'
    ledger=DollarLedger(LEDGER)
    prior=ROOT/'eval/results/smoke_2026-10-14_funded.json'
    ledger.seed_smoke(prior)
    if OUTPUT.exists():
        report=json.loads(OUTPUT.read_text())
    else:
        old=json.loads(prior.read_text())
        report={'scope':'eight public few-shot smoke examples, not held-out evaluation', 'prior_evidence':str(prior.relative_to(ROOT)),
                'questions':[q for q in old['questions'] if q['status']=='passed']}
    def save():
        report['ledger']=ledger.summary()
        OUTPUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
    agent=PacedOwnerAgent()
    agent.client=DollarClient(agent.client,ledger,'smoke_continuation')
    examples=yaml.safe_load((HERE/'few_shot.yaml').read_text())['examples']
    try:
        for q in examples[len(report['questions']):]:
            result=agent.ask(q['question'])
            expected=execute(q['sql'])[1]
            passed=compare_rows(expected,result['rows'],{'abs':1e-8,'rel':1e-8},ordered=True) and not result['clarification']
            report['questions'].append({'question':q['question'],'status':'passed' if passed else 'mismatch','result':result,'reference_rows':expected})
            save()
            print('Smoke complete:',len(report['questions']),'status:',report['questions'][-1]['status'],flush=True)
        report['status']='completed'
    except Exception as error:
        report['status']='stopped'
        report['error']=str(error) if isinstance(error,AssistantError) else type(error).__name__
    save()
    print(json.dumps({'status':report['status'],'questions':len(report['questions']),'cost':ledger.summary()['charged_or_reserved_usd']}))
    return int(report['status']!='completed' or any(q['status']!='passed' for q in report['questions']))

if __name__=='__main__':
    raise SystemExit(main())
