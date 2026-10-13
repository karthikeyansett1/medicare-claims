"""Offline gold validation by default. Live calls require --live and explicit budgets."""
import argparse
import csv
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import time

import yaml
from assistant.database import execute
from assistant.guardrails import validate_sql
from assistant.sql_agent import Agent, RULES, context

ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = {'simple_lookup': 8, 'aggregation': 8, 'method_specific': 8,
              'measure_definition': 10, 'method_comparison': 6, 'denominator_trap': 5, 'ambiguous': 5}
TAXONOMY = [
    'Wrong attribution method used or method ignored',
    'Measure exclusions ignored (for example, December discharges counted)',
    'Wrong denominator (member counts instead of member months)',
    'Paid vs. allowed confusion', 'Join fan-out (cost double counted)',
    'Wrong time window or year', 'Minimum panel filter missing',
    'Answered an ambiguous question instead of asking',
    'SQL error or guardrail rejection', 'Other (describe)',
]


def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()


def cell_equal(a, b, absolute, relative):
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    if isinstance(a, (int, float, Decimal)) and isinstance(b, (int, float, Decimal)):
        a, b = Decimal(str(a)), Decimal(str(b))
        if not a.is_finite() or not b.is_finite():
            return False
        return abs(a-b) <= max(absolute, relative * max(abs(a), abs(b)))
    return type(a) is type(b) and a == b


def compare_rows(expected, actual, tolerance=None, ordered=False):
    """Column labels ignored; column position/type/duplicates retained.

    Tolerance is not an equivalence relation: bipartite matching prevents greedy
    near-number collisions from producing a false negative. No rounded hashes.
    """
    tolerance = tolerance or {}
    absolute = Decimal(str(tolerance.get('abs', 0)))
    relative = Decimal(str(tolerance.get('rel', 0)))
    if not absolute.is_finite() or not relative.is_finite() or absolute < 0 or relative < 0:
        raise ValueError('Tolerance must be finite and nonnegative.')
    a = [tuple(r.values()) if isinstance(r, dict) else tuple(r) for r in expected]
    b = [tuple(r.values()) if isinstance(r, dict) else tuple(r) for r in actual]
    if len(a) != len(b):
        return False
    def eq(x, y):
        return len(x) == len(y) and all(cell_equal(v, w, absolute, relative) for v, w in zip(x, y))
    if ordered:
        return all(eq(x, y) for x, y in zip(a, b))
    edges = [[j for j, y in enumerate(b) if eq(x, y)] for x in a]
    matched = {}
    def augment(i, seen):
        for j in edges[i]:
            if j in seen:
                continue
            seen.add(j)
            if j not in matched or augment(matched[j], seen):
                matched[j] = i
                return True
        return False
    return all(augment(i, set()) for i in range(len(a)))


def load_questions(path):
    data = yaml.safe_load(Path(path).read_text())
    questions = data['questions'] if isinstance(data, dict) else data
    if not isinstance(questions, list) or len(questions) != 50:
        raise ValueError('Exactly 50 held-out questions required.')
    counts = dict.fromkeys(CATEGORIES, 0)
    ids, texts = set(), set()
    normalize = lambda text: ' '.join(text.split()).casefold()
    fewshots = {normalize(example['question']) for example in yaml.safe_load((ROOT / 'assistant/few_shot.yaml').read_text())['examples']}
    for q in questions:
        if not isinstance(q.get('id'), str) or q['id'] in ids:
            raise ValueError('Question IDs must be unique strings.')
        ids.add(q['id'])
        if not isinstance(q.get('question'), str) or not q['question'].strip() or q['question'] in texts:
            raise ValueError('Questions must be nonempty and unique.')
        if normalize(q['question']) in fewshots:
            raise ValueError('Held-out question duplicated in few-shots.')
        texts.add(q['question'])
        counts[q['category']] += 1
        sql = q.get('gold_sql', '')
        if q['category'] == 'ambiguous':
            if sql.strip():
                raise ValueError('Ambiguous gold SQL must be empty.')
        else:
            validate_sql(sql)
        compare_rows([], [], q.get('tolerance'))
        defaults = q.get('defaults', {})
        if defaults.get('sample', 1) not in (1, 2) or defaults.get('year', 2009) not in (2009, 2010) or defaults.get('method', 'A_visits') not in ('A_visits', 'B_allowed'):
            raise ValueError('Invalid defaults.')
    if counts != CATEGORIES:
        raise ValueError(f'Category counts differ: {counts}')
    return questions


def fingerprint(questions_path, model, build_id):
    files = ['assistant/sql_agent.py', 'assistant/guardrails.py', 'assistant/database.py',
             'assistant/semantic_layer.yaml', 'assistant/measure_definitions.md', 'assistant/few_shot.yaml',
             'eval/run_eval.py']
    hashes = {f: digest((ROOT/f).read_bytes()) for f in files}
    for f in ['dbt_project/target/manifest.json', 'dbt_project/target/run_results.json', 'docs/sample2_integration_verification.json']:
        if (ROOT/f).exists():
            hashes[f] = digest((ROOT/f).read_bytes())
    return {'questions_sha256': digest(Path(questions_path).read_bytes()), 'files': hashes,
            'prompt_sha256': digest(RULES + '\n\n' + context()), 'model': model,
            'data_build_id': build_id, 'temperature': 'omitted: model support unverified'}


def validate_gold(questions, output, metadata):
    results = []
    for q in questions:
        start = time.monotonic()
        if q['category'] == 'ambiguous':
            results.append({'id': q['id'], 'status': 'clarification_expected', 'rows': None})
            continue
        checked, rows = execute(q['gold_sql'])
        results.append({'id': q['id'], 'status': 'executed_read_only', 'rows': len(rows),
                        'sql_sha256': digest(checked), 'latency_s': round(time.monotonic()-start, 3)})
    report = {'kind': 'offline_gold_validation_not_model_accuracy', 'metadata': metadata,
              'executed_sql': sum(r['status'] == 'executed_read_only' for r in results),
              'clarifications': sum(r['status'] == 'clarification_expected' for r in results), 'results': results}
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(json.dumps(report, indent=2)+'\n')
    return report


class EvaluationBudget(RuntimeError):
    pass


class BoundedAgent(Agent):
    def __init__(self, max_calls, max_tokens, state, persist):
        super().__init__()
        self.max_calls, self.max_tokens = max_calls, max_tokens
        self.state, self.persist = state, persist
        self.generated_plans = []

    def _call(self, messages, structured=False):
        reservation = len(json.dumps(messages, ensure_ascii=False).encode()) + 2000 + 3000
        if self.state['calls_reserved'] >= self.max_calls or self.state['tokens_reserved'] + reservation > self.max_tokens:
            raise EvaluationBudget('Evaluation call/token reservation budget exhausted.')
        self.state['calls_reserved'] += 1
        self.state['tokens_reserved'] += reservation
        self.persist()  # Durable reservation before any billable call, including failures.
        raw = super()._call(messages, structured)
        if structured:
            try:
                self.generated_plans.append(json.loads(raw))
            except ValueError:
                pass
        return raw


def failure_label(q, result, error):
    if error:
        return TAXONOMY[9], 'Operational error, not a measured methodology failure; inspect safe error metadata.'
    if q['category'] == 'ambiguous':
        return TAXONOMY[7], 'Expected nonempty clarification with empty SQL.'
    return TAXONOMY[9], 'Result values/shape/order differ from gold; methodology requires review.'


def usage_total(usage, field):
    """An incomplete measurement is unknown, not a zero or a partial total."""
    if not usage or any(item.get(field) is None for item in usage):
        return None
    return sum(item[field] for item in usage)


def run_live(questions, directory, metadata, version, repetitions, max_calls, max_tokens, resume=False, agent_factory=BoundedAgent):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    state_path, rows_path = directory/'state.json', directory/'results.jsonl'
    identity = {'metadata': metadata, 'version': version, 'repetitions': repetitions,
                'max_calls': max_calls, 'max_tokens': max_tokens}
    if state_path.exists():
        if not resume:
            raise ValueError('Run exists; use --resume with identical configuration.')
        state = json.loads(state_path.read_text())
        if state['identity'] != identity:
            raise ValueError('Resume identity differs; never mix models/prompts/data/budgets.')
        if state.get('stop_reason'):
            raise ValueError('Stopped runs are immutable; create a fresh run after resolving the cause.')
    else:
        if resume or rows_path.exists():
            raise ValueError('Cannot resume without a matching state file.')
        state = {'identity': identity, 'calls_reserved': 0, 'tokens_reserved': 0}
    def persist():
        tmp = state_path.with_suffix('.tmp')
        tmp.write_text(json.dumps(state, indent=2)+'\n')
        tmp.replace(state_path)
    persist()
    existing = [json.loads(line) for line in rows_path.read_text().splitlines()] if rows_path.exists() else []
    done = {(r['repetition'], r['id']) for r in existing}
    agent = agent_factory(max_calls, max_tokens, state, persist)
    if agent.model != metadata['model']:
        raise ValueError('Configured model does not match run identity.')
    stopped = False
    for repetition in range(1, repetitions+1):
        for q in questions:
            if (repetition, q['id']) in done:
                continue
            start = time.monotonic()
            result, error, passed = {}, '', False
            agent.generated_plans = []
            agent.usage = []
            try:
                gold = execute(q['gold_sql'])[1] if q['gold_sql'].strip() else []
                # Never pass gold SQL, category, expected values or scoring rubric to runtime.
                result = agent.ask(q['question'], **q.get('defaults', {}))
                if q['category'] == 'ambiguous':
                    passed = not result['sql'].strip() and bool(result.get('clarification')) and bool(result['answer'].strip())
                else:
                    passed = bool(result['sql'].strip()) and compare_rows(gold, result['rows'], q.get('tolerance'), q.get('ordered', False))
            except Exception as exc:
                # Avoid raw provider/DB messages, secrets, and row contents in errors.
                error = type(exc).__name__
                if any(code in str(exc) for code in ('credit_balance_exhausted', 'insufficient_quota')):
                    error += ':insufficient_quota'
                # All operational errors stop. Never retry a quota failure across 50 cases.
                stopped = True
            failure, evidence = ('', '') if passed else failure_label(q, result, error)
            usage = result.get('usage', getattr(agent, 'usage', []))
            record = {'id': q['id'], 'question': q['question'], 'repetition': repetition,
                      'pass': passed, 'generated_sql': result.get('sql', (agent.generated_plans[-1].get('sql', '') if agent.generated_plans else '')), 'answer': result.get('answer', ''),
                      'generated_plans': agent.generated_plans,
                      'error': error, 'failure_type': failure, 'failure_evidence': evidence,
                      'failure_review': '' if passed else 'provisional_automated',
                      'latency_s': round(time.monotonic()-start, 3), 'usage': usage,
                      'input_tokens': usage_total(usage, 'input_tokens'),
                      'output_tokens': usage_total(usage, 'output_tokens')}
            with rows_path.open('a') as stream:
                stream.write(json.dumps(record, default=str)+'\n')
                stream.flush()
            existing.append(record)
            if stopped:
                state['stop_reason'] = error
                break
        if stopped:
            break
    state['completed_questions'] = len(existing)
    state['complete'] = len(existing) == len(questions)*repetitions and not stopped
    persist()
    with (directory/'results.csv').open('w', newline='') as stream:
        fields = ['id','question','repetition','pass','generated_sql','answer','error','failure_type','failure_evidence','failure_review','latency_s','input_tokens','output_tokens']
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(existing)
    summary = {'complete': state['complete'], 'completed_questions': len(existing), 'stop_reason': state.get('stop_reason'),
               'accuracy': None, 'note': 'Incomplete runs have no reported accuracy; faithfulness requires separate review.'}
    if state['complete']:
        scores = [sum(r['pass'] for r in existing if r['repetition']==i)/len(questions) for i in range(1,repetitions+1)]
        summary.update(accuracy=scores, range=[min(scores), max(scores)])
    (directory/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--questions', type=Path, default=ROOT/'eval/questions.yaml')
    parser.add_argument('--live', action='store_true', help='Explicitly authorize billable provider calls for this invocation.')
    parser.add_argument('--version', default='v1')
    parser.add_argument('--repetitions', type=int, choices=(1,2,3), default=1)
    parser.add_argument('--model')
    parser.add_argument('--data-build-id', required=True, help='Verified immutable sample/build identifier, not an arbitrary label.')
    parser.add_argument('--max-calls', type=int)
    parser.add_argument('--max-tokens', type=int)
    parser.add_argument('--output', type=Path, default=ROOT/'eval/results/offline_gold_validation.json')
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    questions = load_questions(args.questions)
    if args.live and (not args.model or not args.max_calls or args.max_calls < 1 or not args.max_tokens or args.max_tokens < 1):
        parser.error('--live requires --model, positive --max-calls and --max-tokens')
    if args.live:
        import os
        os.environ['LLM_MODEL'] = args.model
        if args.output == ROOT/'eval/results/offline_gold_validation.json':
            parser.error('--live requires an explicit --output run directory')
    meta = fingerprint(args.questions, args.model or 'not_called', args.data_build_id)
    if args.live:
        report = run_live(questions, args.output, meta, args.version, args.repetitions, args.max_calls, args.max_tokens, args.resume)
        print(json.dumps(report))
    else:
        report = validate_gold(questions, args.output, meta)
        print(f"Offline validation: {report['executed_sql']} gold queries executed; {report['clarifications']} clarification cases. No model accuracy measured.")


if __name__ == '__main__':
    main()
