# Step 12 — grounded analytics assistant

## What changed

The Streamlit app accepts a question plus default sample, performance year and
attribution method (1 / 2009 / A_visits). It sends the canonical semantic layer,
measure definitions and eight training examples to the configured OpenAI model.
A Responses API structured plan contains assumptions, SQL and clarification.
Ambiguous or unavailable metrics return empty SQL. Valid SQL executes through a
dedicated `assistant_ro` login; a second model request explains actual rows.
One SQL repair is allowed after a validation or database error. There are no canned
answers presented as model results.

The seven-table semantic layer was drafted from dbt's manifest, then curated and
compared with the live PostgreSQL column catalog. Every column has a meaning;
grains and valid sample-aware joins are explicit. All definitions now live in
`assistant/measure_definitions.md`; the former docs file links to it.

## Why these choices matter

The model can generate plausible but incorrect analysis. Medical Medicare-paid
cost excludes gross prescription cost; annualized rates use member-month proxy
exposure; provider rankings require at least 20 members. Facts must be aggregated
before joining to avoid fanout. Readmission exclusions and annual FFS proxies
remain visible. The prompt and few-shots teach these rules; they do not prove
semantic correctness. The held-out evaluation in Step 13 remains necessary.

`mart_cost_by_ccs` is already pooled across all loaded samples and has no sample
column. Sample-specific CCS questions require clarification. Explicitly pooled
CCS requests can run. Provider specialty, real provider identities and causal
quality claims cannot be answered from this warehouse.

## Execution boundaries

- SQLglot parses PostgreSQL and traverses the full AST. Only a single SELECT with
  SELECT-only, nonrecursive CTEs is accepted. It rejects nested writes, SELECT
  INTO, row locks, system/other tables, table functions and unapproved functions.
- Physical tables require exact schema qualification. SQLglot resolves aliases,
  CTEs and columns against the checked schema, rejecting unknown/ambiguous columns.
  Joins require ON/USING. Semantic join correctness still needs evaluation.
- The output limit is at most 500 even when a larger limit was requested.
  Custom operators and string concatenation are rejected. Server cursors stream
  rows and reject serialized rows above 64 KB or total output above 1 MB. Database
  execution uses a read-only transaction, 20-second cumulative execution deadline (including server-cursor fetches),
  a statement timeout set to the remaining deadline, and a 2-second lock
  timeout. The role lacks write/create privileges and can SELECT only seven tables.
- `sql/roles.sql` and `assistant.setup_role` create/configure the role idempotently.
  Password generation writes only ignored `.env` with mode 0600. Owner setup
  removes PUBLIC temp/schema-create access in this dedicated project database and
  PUBLIC execution of application-defined functions. PostgreSQL built-ins still
  exist; the AST function allowlist is the application boundary against misuse.
- Exact per-model dbt grants survive table replacement; the dbt runner provisions
  the role before build/run. No grant gives access to all gold or marts tables.
- Each session permits ten questions; a persistent SQLite ledger atomically
  reserves input-byte upper bounds plus 3,000 output tokens before each API call.
  Defaults: 6 calls/minute, 60 calls/day, 1,000,000 reserved tokens/day across all
  sessions/processes sharing that ledger. Failed requests retain reservations.
  SDK retries are disabled; SQL repair can produce at most three calls per question.
  API requests time out after 60 seconds. Actual usage and latency are logged.
- Logs are ignored and private, and omit questions, answers, raw provider errors
  and credentials. Result explanations receive a bounded row excerpt, with its
  length disclosed to the model. Provider storage is disabled (`store=false`).

## Run and verify

```sh
make setup
make assistant-role
make test
RUN_DB_TESTS=1 .venv/bin/python -m pytest tests/test_assistant_database.py -q
make assistant
# Billable; sends schema/definitions/question and synthetic result rows to OpenAI:
make assistant-smoke
```

Set `LLM_PROVIDER=openai`, `LLM_API_KEY` and `LLM_MODEL` privately in `.env`.
The model is configurable; this checkpoint preserves `gpt-6-astra`. Temperature
is omitted because model-specific support has not been established. Structured
Outputs use the current SDK's Responses endpoint, strict JSON schema and
`max_output_tokens`. Sources: [official Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs)
and [Responses API reference](https://developers.openai.com/api/reference/python/resources/responses/methods/create).

Implementation verification: full database-enabled suite **114 passed** (3.04s);
47 assistant unit/adversarial tests passed. dbt-aware SQL lint passed all models.
Streamlit AppTest rendered the form with defaults 1/2009/A_visits and no exception.
Four live database
checks passed, including all eight few-shot queries, exact grants, schema equality,
and INSERT denial both with default read-only mode and with that mode explicitly
disabled against a disposable probe table. No warehouse data was modified.

Real API smoke status (2026-10-12): the user explicitly authorized synthetic
payload export and billable testing. Two bounded smoke planning requests reached
OpenAI but failed HTTP 429 before producing SQL. One final minimal 32-output-token
diagnostic established `code=credit_balance_exhausted`,
`type=insufficient_quota`, with no Retry-After header. The message referenced
billing. No query or answer-generation call ran, and no token usage was returned.
Zero successful generations is the measured outcome; dollar cost is unknown,
not estimated or fabricated. The user requested continuing without paid evaluation.
Do not rerun `make assistant-smoke` unless the user later authorizes live evaluation;
API authentication alone does not establish generation access.
All independent code, schema, SQL examples and permission tests are complete.
Live validation is **deferred by user request**; a successful authorized smoke
would still be required to complete the live LLM checkpoint.
this implementation must not be described as end-to-end API-verified yet.

## Interview explanation

“I separate the model's proposal from the execution authority. The model gets
curated business definitions and returns a structured plan. An AST policy and a
least-privilege database role independently constrain execution, and the final
answer is generated only from returned rows. I explicitly distinguish security
validation from analytic correctness: safe SQL can still use the wrong grain,
so held-out denominator, attribution and ambiguity tests are the next step.”

For public deployment, persist the shared budget ledger (or replace it with a
shared transactional service), add authenticated/rate-limited access, and configure
provider project spending limits. A token reservation is not a verified dollar
cap; model pricing and account billing govern actual charges. Session state alone
is resettable; the server-wide ledger is the durable backstop. This checkpoint
binds the local app to loopback by default.

## Publication

The verified implementation is published from `codex/step-12-assistant`, based on
`codex/step-11b-sample2`. This publication does not claim successful live generation
or a completed paid evaluation. The next checkpoint builds the evaluation harness
without paid calls. Earlier draft PRs remain unmerged.
