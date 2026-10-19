# Access-controlled live fixture assistant (deployment preparation)

Entrypoint: `deployment/live/app.py`; Python 3.11; dependency file alongside the entrypoint. This is separate from the existing free static dashboard. It queries only the hosted deterministic 1,000-member Sample 1 fixture, not the full Samples 1 and 2 warehouse.

## Owner setup, once

After reviewing and authorizing external database changes, the owner can run `python -m deployment.live.prepare --apply-bootstrap` locally. It reads existing owner/query/API credentials from ignored local configuration, creates a separate budget role and fixed campaign, and writes `.runtime/streamlit-live-secrets.toml` with mode 600. It never prints credential values or calls OpenAI. The file contains the private access code and the four server-side Streamlit secret values. Paste it into the application's private secrets settings; never commit it. The administrator DSN is not included. A preexisting campaign, role or secrets file makes setup refuse rather than reset spending. Credentials are written exclusively and fsynced before the DDL transaction commits. A write failure rolls back DDL and removes only the newly created incomplete file. If commit acknowledgement is lost, the complete private file is retained for explicit owner recovery; initialization never resets an existing campaign.

The human owner completes Streamlit/GitHub sign-in and terms. Select the reviewed branch and entrypoint, Python 3.11, and paste server-side secrets. Do not enable until read-only configuration/role checks and offline tests have passed. This preparation does not itself create hosting or send an API call.

## Fixed allowance

One database campaign has a **$5 lifetime** limit, shared across all users, processes and replicas. PostgreSQL locks a singleton row, verifies the cost calculation, checks 3 calls/minute and 30/day, records a reservation and commits before API dispatch. A failed commit or unavailable DB prevents dispatch. The budget login has only schema usage and EXECUTE on two fixed security-definer functions, no table-write privileges and no reset function. Runtime cannot create another campaign or raise the cap with environment variables. Keep the same database; deleting/restoring it or owner-replacing the campaign is outside the runtime guarantee.

Reservations count every serialized UTF-8 byte as an input token, add 8,192 framing tokens, cap input at 70,000 and output at 3,000, and charge $12.50/M input (the higher cache-write rate) and $50/M output. Exact `gpt-6-astra`, standard tier and low reasoning are fixed; tools, images, external context and alternate parameters are rejected. No refunds, retries or usage-based releases occur. This conservative allowance may cover only a few complete questions; a planning call can consume allowance even if a subsequent explanation cannot be reserved. Actual provider spend may be lower. This cap covers this app's requests, not unrelated API-key use or provider price changes. [Pricing source](https://developers.openai.com/api/docs/models/gpt-6-astra), checked October 17, 2026.

## Access and query boundary

A high-entropy random code is checked in constant time before any DB or API-client initialization. The submitted code is neither sent to the model nor logged/exported; the form clears on submit. Share it only with intended testers. This is shared-code access, not per-user accounts. A leaked code can consume the small shared allowance; rotate it in private secrets to revoke access.

The query credential must be `medicare_demo_ro`, the budget credential `medicare_live_budget`, both on the same database with TLS certificate verification (`sslmode=verify-full` with the pinned certifi CA bundle supplied at connection time; no machine-specific CA path is serialized in secrets). The app verifies role properties, exact seven query SELECT grants, fixed fixture counts and Sample 1-only data. SQL retains the existing AST allowlist, read-only transaction, execution deadlines and row/byte caps. Both connections use plain connect followed by transaction-local settings for hosted pooler compatibility.

The UI and every answer explicitly identify fixture scope. Common Sample 2/full-sample requests are clarified without model calls; the model also receives an explicit deployment-scope override. SQL can only access the verified fixture. Claims about full-sample/general-population performance are unsupported.

Run offline checks with `python -m pytest tests/test_live_budget.py tests/test_live_app.py -q`. These use mocks and make no API/database calls. Real PostgreSQL concurrency/privilege verification remains a separate owner-authorized deployment check; mocks do not establish hosted SQL correctness.

## Hosted verification completed

On October 19, 2026, the one-time bootstrap and owner-authorized hosted probes passed. [Sanitized evidence](verification.json) records verified TLS, runtime role/effective privileges and fixture identity, query-role write/budget-function denial, budget-role least privilege and minute limits, fixed lifetime-cap/day-limit function checks using temporary owner transaction fixtures, and serialization across two real budget-login connections. All probe rows and spending rolled back: **$0 reserved, zero reservation rows, zero API calls**. PostgreSQL identity sequence values may advance during these rolled-back checks. No runtime roles were granted owner membership to make tests pass.
