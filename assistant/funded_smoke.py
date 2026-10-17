"""Opt-in real API smoke, with nonrefundable pre-dispatch dollar reservations.

Run: python -m assistant.funded_smoke --output eval/results/smoke_DATE.json
Only public few-shot questions are used; this is not held-out evaluation.
"""
import argparse
import json
from pathlib import Path
from datetime import datetime, timezone
from types import SimpleNamespace
import yaml
from assistant.sql_agent import Agent, AssistantError, HERE
from assistant.database import execute

LIMIT_USD = 5.0
MODEL = 'gpt-6-astra'
PRICING_URL = 'https://developers.openai.com/api/docs/models/gpt-6-astra'


def request_bound(kwargs):
    if kwargs.get('model') != MODEL or kwargs.get('service_tier') != 'default':
        raise ValueError('Smoke requires reviewed Astra standard pricing.')
    if kwargs.get('tools') or kwargs.get('previous_response_id'):
        raise ValueError('Only self-contained text requests are priced.')
    output = kwargs.get('max_output_tokens')
    if not isinstance(output, int) or not 1 <= output <= 3000:
        raise ValueError('Invalid output cap.')
    # Every UTF-8 byte is counted as one token, including JSON schema, with
    # 8,192 extra tokens for protocol/schema framing. Refuse long context.
    inputs = len(json.dumps(kwargs, ensure_ascii=False).encode('utf-8')) + 8192
    if inputs > 70000:
        raise ValueError('Smoke input exceeds reviewed short-context bound.')
    # Cache writes can cost more than uncached input; reserve that upper rate.
    return inputs, (inputs * 12.5 + output * 50) / 1_000_000


class Meter:
    def __init__(self, client, report, save):
        self.client, self.report, self.save = client, report, save
        self.responses = SimpleNamespace(create=self.create)

    def create(self, **kwargs):
        kwargs.update(service_tier='default', reasoning={'effort': 'low'})
        inputs, dollars = request_bound(kwargs)
        reserved = sum(c['reserved_usd'] for c in self.report['calls'])
        if reserved + dollars > LIMIT_USD:
            raise AssistantError('Smoke dollar reservation limit reached before dispatch.')
        entry = {'input_token_upper_bound': inputs, 'max_output_tokens': kwargs['max_output_tokens'],
                 'reserved_usd': dollars, 'usage': None, 'status': 'reserved_unknown'}
        self.report['calls'].append(entry)
        self.save()  # Persist before network; unknown or failed calls retain reservation.
        response = self.client.responses.create(**kwargs)
        entry.update(status=response.status, response_model=response.model,
                     service_tier=getattr(response, 'service_tier', None),
                     usage=response.usage.model_dump() if response.usage else None)
        if response.usage:
            u = response.usage
            cached = getattr(u.input_tokens_details, 'cached_tokens', 0) or 0
            writes = getattr(u.input_tokens_details, 'cache_write_tokens', 0) or 0
            entry['standard_usage_estimate_usd'] = ((u.input_tokens-cached-writes)*10 + cached + writes*12.5 + u.output_tokens*50)/1_000_000
            entry['usage_cost_upper_usd'] = (u.input_tokens*12.5 + u.output_tokens*50)/1_000_000
        self.save()
        return response


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--questions', type=int, default=1, choices=range(1, 9))
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # No accidental replay into a prior evidence file.
    with args.output.open('x') as file:
        file.write('{}')
    report = {'started_utc': datetime.now(timezone.utc).isoformat(), 'scope': 'public few-shot smoke, not held-out score',
              'model': MODEL, 'limit_usd': LIMIT_USD, 'pricing_url': PRICING_URL,
              'pricing_verified_date': '2026-10-14', 'calls': [], 'questions': []}
    def save():
        report['reserved_usd'] = sum(c['reserved_usd'] for c in report['calls'])
        report['known_usage_estimate_usd'] = sum(c.get('standard_usage_estimate_usd', 0) for c in report['calls'])
        report['unknown_usage_calls'] = sum(c['usage'] is None for c in report['calls'])
        args.output.write_text(json.dumps(report, indent=2, default=str)+'\n')
    try:
        agent = Agent()
        if agent.model != MODEL:
            raise AssistantError('Configured model differs from reviewed smoke model.')
        agent.client = Meter(agent.client, report, save)
        examples = yaml.safe_load((HERE/'few_shot.yaml').read_text())['examples']
        for example in examples[:args.questions]:
            item = {'question': example['question'], 'status': 'started'}
            report['questions'].append(item)
            save()
            result = agent.ask(example['question'])
            _, expected = execute(example['sql'])
            # Compare values, allowing harmless output alias differences.
            actual_values = [list(row.values()) for row in result['rows']]
            expected_values = [list(row.values()) for row in expected]
            item.update(status='passed' if actual_values == expected_values and not result['clarification'] else 'mismatch',
                        result=result, reference_rows=expected)
            save()
            if item['status'] != 'passed':
                break
        report['status'] = 'completed'
    except Exception as error:
        # Only known application errors may be shown; never dump provider bodies.
        report['status'] = 'stopped'
        report['error'] = str(error) if isinstance(error, AssistantError) else type(error).__name__
    finally:
        report['finished_utc'] = datetime.now(timezone.utc).isoformat()
        save()
    print(json.dumps({k: report[k] for k in ['status','reserved_usd','known_usage_estimate_usd','unknown_usage_calls']}))
    print('Question statuses:', [q['status'] for q in report['questions']])
    if report.get('error'):
        print(report['error'])
    return 0 if report['status'] == 'completed' and all(q['status']=='passed' for q in report['questions']) else 1

if __name__ == '__main__':
    raise SystemExit(main())
