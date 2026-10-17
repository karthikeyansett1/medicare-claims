# Human review: free portfolio showcase and frozen AI answers

Status: **PENDING — no human review has been claimed.** Reviewer: ______ Date: ______

Allow 15–30 minutes. This is an owner review, not clinical validation or an independent audit. Review the existing public showcase and saved v2 repetition-1 answers without calling an API or paying for hosting. The 15 question IDs were selected before paid outputs existed. Prior 15/15 scores were Codex agent reviews; do not copy those scores into your human decision.

## 1. Check the public story (about 5 minutes)

Open [the public dashboard](https://karthikeyansett1-medicare-provider-performance.static.hf.space). Visitors can explore the project and see examples; they cannot send arbitrary questions to a live model. This is the intended free portfolio deployment. Live public AI is not required or planned for this delivery.

- [ ] Overview: choose sample, year, and method; confirm displayed scope changes and synthetic-data labeling is visible.
- [ ] Provider scorecard: confirm a provider NPI remains text, including leading zeros, and small-panel warnings/thresholds are clear.
- [ ] Method comparison: inspect a provider movement example and confirm cost deciles are not presented as clinical quality rankings.
- [ ] Conditions: confirm the pooled-sample scope is clear; this mart cannot support sample-specific filtering.
- [ ] Assistant: open all four saved examples; confirm they say saved SQL demonstration and use a separate 1,000-member fixture. Full dashboard aggregates use both complete samples; these fixture outputs must not be represented as the full 23-million-row warehouse.
- [ ] Confirm there is no public API-key entry, arbitrary SQL execution, or promise of a live AI response. Record any misleading wording rather than trying to activate paid calls.

Public review decision: PENDING. Notes: ______

## 2. Review the 15 frozen answers (about 15–20 minutes)

Open [human_review_template.csv](human_review_template.csv) in a spreadsheet editor. Each row contains the original question, complete model answer, generated SQL, executed result rows, and factual reference checks. All human fields start PENDING. Read the answer before the reference checks to reduce anchoring. Use `assistant/measure_definitions.md` when a definition is unclear. These answers used the full local warehouse; they are separate from the four public fixture demonstrations.

For each row, mark each rubric field PASS, FAIL, or UNCERTAIN:

1. Scope and method: sample, year, provider, attribution method, and eligible/reportable population match the question and SQL.
2. Numbers and units: every numerical claim follows from returned rows, with defensible display rounding. Do not invent a numerator or denominator absent from the results.
3. Denominator and definition: PMPM uses exposure months; readmissions use eligible index episodes; utilization uses the specified exposure. Medical paid, professional allowed, and Rx gross are distinct.
4. Caveats and faithfulness: no unsupported causal/provider-quality claims; annual enrollment is a proxy; pooled scope, NULL/empty results, and relevant limitations are accurately explained.

Set overall human_status to PASS only if all four checks pass. A failed check means FAIL; unresolved uncertainty means UNCERTAIN. Enter your name, actual review date, and a concrete note for every FAIL/UNCERTAIN. Do not change frozen answers or reference SQL to make a result pass. Report the numerator and reviewed denominator, for example “12/15 pass, 2 uncertain, 1 fail, reviewed by [name] on [date].” This review is answer faithfulness, not a replacement for the strict 49/50 execution score or proof of unseen-question performance.

### Expected checks by question

- **Q01 — PENDING:** How many full-year FFS members are recorded in sample 2 for 2009? Reference checks: COUNT=72650; sample 2/year 2009/full-year flag. Explains annual-count proxy and attribution inapplicable.
- **Q04 — PENDING:** For synthetic NPI 0888901330 in sample 1, 2009, Method A, return panel size and proxy member months. Reference checks: Panel=388, months=4641; sample 1/2009/A_visits/NPI match; proxy coverage limitation stated.
- **Q09 — PENDING:** Sum medical Medicare payments and gross prescription costs separately for all sample 2 cost records assigned to 2009. Reference checks: Medical=506357040 and Rx gross=133903570; sample 2/2009, all cost records, no attribution/eligibility restriction.
- **Q12 — PENDING:** What are total outpatient claims and ED-coded outpatient claims for sample 1 cost records in 2009? Reference checks: Outpatient=322358, ED=26334; sample 1/2009; HCPCS claims proxy and not unique visits stated.
- **Q17 — PENDING:** List the 7 largest reportable panels in sample 2 for 2009 under Method B; return NPI and panel size, breaking ties by NPI ascending. Reference checks: All seven NPI/count pairs match query order including 215-member tie; sample 2/2009/B_allowed and reportable threshold stated.
- **Q20 — PENDING:** For sample 1 in 2010, how many Method B winners have at least one missing allowed line? Reference checks: Count=0; sample 1/2010/B_allowed; explains winning member-years, not unique providers; allowed distinct from paid.
- **Q25 — PENDING:** For sample 2 in discharge year 2010, return eligible index episodes, 30-day readmissions, and their overall readmission proportion, including unattributed members. Reference checks: 356/8337=4.270121%; sample 2 discharge year 2010; attributed and unattributed included, canonical index eligibility stated.
- **Q28 — PENDING:** For sample 2 in 2009, return professional Medicare paid and professional allowed totals separately. Reference checks: Paid=165331240, allowed=213011010; sample 2/2009; distinct payment concepts, no attribution restriction.
- **Q31 — PENDING:** Sum medical paid for sample 2 members attributed under Method A in 2009, joining the canonical member-year cost summary once per member. Reference checks: SUM=338974010; sample 2/2009/A_visits; sample-aware one-member-year join, Rx exclusion and adjustments stated.
- **Q34 — PENDING:** For sample 2 eligible members in 2010 with a true CHF flag, return total medical paid and the total count of missing medical payments. Reference checks: Medical=94103300; missing count=0; sample 2/2010/eligible/CHF true; no attribution filter and no imputation.
- **Q35 — PENDING:** In sample 1 for 2010, how many members assigned under both methods switch NPI between A and B? Reference checks: COUNT=39381; sample 1/2010, both methods non-null differing NPI; no minimum panel; no costs.
- **Q38 — PENDING:** Among sample 2 providers reportable under both methods in 2010, how many move at least 3 raw PMPM deciles? Reference checks: COUNT=44; sample 2/2010, both methods reportable, non-null deciles, absolute movement>=3; medical-paid PMPM definition.
- **Q41 — PENDING:** For synthetic NPI 0888901330 in sample 1, 2009, Method A, return ED-coded claims, member months, and the annualized ED claims per 1,000. Reference checks: 118 claims/4641 months*12000=305.106658; sample 1/2009/A_visits; ED proxy and annual-count exposure.
- **Q43 — PENDING:** For reportable panels in sample 1, 2009, Method B, calculate pooled medical PMPM weighted by member-month exposure. Reference checks: SUM-paid/SUM-months=525.227916; sample 1/2009/B_allowed, reportable>=20, Rx excluded; not unweighted provider average.
- **Q45 — PENDING:** For all attributed panels in sample 1, 2010, Method B, calculate the annualized merged admission rate per 1,000 using exposure months. Reference checks: Returned rate=152.6717557251908397, formatted 152.67; sample 1/2010/B_allowed, all panels including small. Explanation correctly states SUM admissions / SUM exposure months *12000, annual exposure proxy and merged admission-year episode definition. Does not invent unreturned numerator/denominator totals.

### View one original answer offline

From the repository root, run this command, changing Q01 to another ID. It only reads saved JSON; it does not query PostgreSQL or call OpenAI.

```sh
.venv/bin/python - Q01 <<'PYVIEW'
import json, sys
from pathlib import Path
path = Path('eval/results/v2_2026-10-16_resumed/results.jsonl')
for line in path.read_text().splitlines():
    row = json.loads(line)
    if row['id'] == sys.argv[1] and row['repetition'] == 1:
        for key in ['id', 'question', 'answer', 'generated_sql', 'result_rows']:
            print(key.upper(), json.dumps(row[key], indent=2, ensure_ascii=False))
        break
else:
    raise SystemExit('Question not found')
PYVIEW
```

## 3. Check boundaries without paid requests (about 3–5 minutes)

Run the mocked clarification and SQL guardrail tests. These use local validation and mocked model responses, not the API or a database. DROP/DELETE examples are only parsed, never executed.

```sh
.venv/bin/python -m pytest -q tests/test_guardrails.py tests/test_assistant.py::test_clarification_never_queries
```

- [ ] Dangerous-write rejection: the parametrized guardrail tests reject DROP, nested DELETE, SELECT INTO, and other forbidden constructs.
- [ ] Ambiguity: the mocked “Who is best?” case produces clarification and must not execute SQL. Also inspect frozen Q46–Q50 with the offline command; each should clarify rather than claim an unsupported answer.
- [ ] Blank question: run the offline check below. Invalid whitespace is rejected before a provider call. The static public showcase has no arbitrary-question input, so this is a local assistant boundary only.

```sh
.venv/bin/python - <<'PYBLANK'
from assistant.sql_agent import Agent, AssistantError
try:
    Agent(client=object()).ask('   ')
except AssistantError as error:
    assert 'Question must contain' in str(error), str(error)
    print('PASS: blank input rejected:', error)
else:
    raise SystemExit('FAIL: blank input was accepted')
PYBLANK
```

Boundary review decision: PENDING. Notes: ______

## Save your decision

Save the completed CSV and your notes; leave original `eval/results` evidence unchanged. Record public review and boundary decisions above separately from the 15 answer decisions. Ask for a correction with the question ID, quoted problem, and expected behavior. No new paid evaluation or live deployment is necessary to finish this review. If you cannot judge a clinical or statistical assumption, mark UNCERTAIN instead of guessing.
