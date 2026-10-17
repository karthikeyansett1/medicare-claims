# Step 13 — held-out evaluation harness

## Current funded validation status — October 16, 2026

The original checkpoint below is historical. Later owner-authorized funding enabled eight public few-shot smoke cases (7/8 strict matches, $0.471646) and a frozen-v1 baseline of **39/50 (78%)** on the 50 evaluation cases. See [v1 evidence](../../eval/results/v1_2026-10-14_resumed/summary.json) and [completed v2 evidence](../../eval/results/v2_2026-10-16_resumed/summary.json). V2 scored **49/50 in each of three runs (98%–98%; population standard deviation 0.00 percentage points)**. Because v1 failures informed general prompt corrections, this is a reused-set regression, not untouched held-out generalization. Codex agent faithfulness review scored 15/15 for v1 and v2 repetition 1; independent human review remains pending. Known usage cost is $6.5081800 plus $1.0315875 retained unknown reservations, totaling $7.5397675 against the $20 cap. Funded owner runners share a $20 ledger including prior smoke, retain unknown-cost reservations, and disable SDK retries. The public website remains a static saved-results demo. Historical deferral and test counts below describe the original publication, not current funding or latest test totals.


## What and why

This checkpoint separates independently authored gold SQL from the assistant's
runtime context. Fifty questions cover lookup (8), aggregation (8), attribution
method (8), measure definitions (10), method comparison (6), denominator traps
(5), and clarification (5). The runtime still receives only the semantic layer,
canonical definitions, eight separate training examples, and the user's question.

The comparator ignores column labels but retains column positions, row shape,
NULLs, booleans, dates and duplicate multiplicity. Numeric comparison uses actual
absolute/relative tolerances, with bipartite matching for unordered rows so nearby
numeric values cannot cause greedy matching collisions. Top-N cases can require
order. A clarification passes only with empty SQL and nonempty clarification text.

## Reproduce without paid calls

```sh
.venv/bin/python -m pytest tests/test_eval.py -q
.venv/bin/python -m eval.run_eval \
  --data-build-id sample-1-2-verified-2026-10-12T19:45:03.851614Z
```

The default executes gold SQL through `assistant_ro`, read-only transactions and
the same seven-table AST policy as the application. It writes only IDs, row
counts, timings and SQL hashes; no member rows are exported. `--live` is required
for billable calls and was **not used** in this checkpoint.

Future live execution additionally requires `--model`, positive `--max-calls`
and `--max-tokens`, a verified `--data-build-id`, `--version v1` or `v2`, and an
`--output` run directory. `--repetitions` supports 1–3. Existing application
minute/day limits remain effective; explicit evaluation budgets do not override
them. Requests reserve conservative tokens durably before dispatch. Any operational
error stops the run. Unknown usage stays null. Actual dollar cost is not inferred.

Resume uses `--resume` and requires identical dataset, prompt, semantic, model,
code, version, repetition and budget identities. Runs stopped by errors are
immutable; after resolving the cause, use a fresh directory. Do not run concurrent
writers against one run directory. The build identifier is an operator-verified
provenance claim; freeze the warehouse during a live run. Local dbt manifest and
run-result hashes are included when available.

## Results and remaining work

Actual validation: **123 tests passed** with `RUN_DB_TESTS=1` (3.10s).
The offline report records **45 gold SQL executions and 5 clarification cases**,
with no API calls. Questions SHA-256:
`3bb09f607c32b14eab51006ecc83f26e9f2ce278e4ee9d1d1078546a9778e199`.

Unit tests verify type/shape/order/duplicate comparison, numeric edge cases,
non-greedy matching, quota termination, gold separation, clarification criteria
and reservation order. Database execution rejects duplicate output labels before
dictionary conversion can silently drop values; the assistant can repair that
validation error with explicit aliases. See the checked-in offline report for actual gold-query
execution results and [summary](../../eval/results/summary.md) for the honest
live status. No paid calls, AI execution score, v1/v2 improvement, variance estimate
or answer-faithfulness score are claimed. Those remain pending by user request.

Every failure has exactly one of the guide's ten labels. Automated labels are
explicitly provisional and include evidence; methodology diagnosis and final
answer faithfulness require review. The review template records reviewer identity,
role, date, run identity, evidence and each rubric dimension. Agent review must
never be described as human review.

## Interview explanation

“I designed a held-out SQL evaluation that checks execution results rather than
SQL wording. It preserves duplicate counts, tolerates small numeric differences,
and checks ordering when rankings matter. I distinguish a working harness and
validated gold answers from actual model performance. Paid evaluation was deferred,
so accuracy and improvement remain unmeasured instead of being fabricated.”

## Publication

The verified offline harness is published in [draft PR #14](https://github.com/karthikeyansett1/medicare-claims/pull/14)
from `codex/step-13-eval`, based on
`codex/step-12-assistant`, under standing checkpoint authorization. This is not
a live model evaluation: accuracy, v1/v2 comparisons, run variance and generated
answer faithfulness remain pending because the user deferred paid evaluation.
Earlier draft PRs remain unmerged; the dashboard is the next checkpoint.

The funded live runner is campaign-specific and intentionally rejects a fresh-clone or replacement ledger. A new paid campaign requires explicit owner setup, authorization and prior-spend accounting. Offline validation and the dashboard remain reproducible without paid access.
