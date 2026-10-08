# Step 0 — Project foundation

Status: local setup verified. User approved the Step 0 GitHub push.

## What we are doing

Created the project folder structure, a Python 3.11 virtual environment, locked
Python dependencies, PostgreSQL 16 Compose configuration, initial database
schemas, a shared connection helper, Make targets, and Git ignore rules.
Initialized a local Git repository on main. Step 0 is prepared for its approved publication.

## Why we are doing it

A repeatable foundation makes later data problems easier to isolate. All scripts
will use the same database settings. Locked dependencies reduce differences
between machines, and ignore rules keep credentials and large downloads out
of version control. The folders separate source data, transformations, analysis,
and user-facing outputs.

## How to explain it if asked

“I started by making the project reproducible. I isolated Python dependencies,
locked their versions, configured PostgreSQL in Docker, and centralized database
connections. I also added checks and a decision log so each later data-processing
step can be explained and verified. I verified the Python dependencies, database health, startup schemas, and
both Python database connection helpers.”

## Verification on 2026-10-08

| Check | Evidence | Result |
| --- | --- | --- |
| Available storage | `df -h .`: about 140 GiB available | Pass |
| Python environment | `.venv/bin/python --version`: 3.11.16 | Pass |
| Required imports | psycopg, dbt, sqlglot and ingest.db import successfully | Pass |
| Dependency compatibility | `uv pip check --python .venv/bin/python`: 66 packages compatible | Pass |
| dbt adapter | dbt reports core 1.12.5 and postgres adapter 1.11.0 | Pass for local installation; latest-version lookup unavailable |
| Compose syntax | `PG_PASSWORD=validation-only docker compose config --quiet` exits 0 | Pass |
| Python syntax | AST parse of ingest Python files | Pass |
| Local Git | Initialized main | Pass |
| Ignore rules | `git check-ignore` matches .env, virtual environment, Python runtime, raw/extracted data, assistant logs | Pass |
| PostgreSQL runtime | Docker 27.5.1; `make db-up` reports container healthy; PostgreSQL 16.15 | Pass |
| Docker engine | User started Docker; engine access verified | Pass |
| Live connection and schemas | `make verify`: psycopg connects and bronze/analysis schemas exist | Pass |
| SQLAlchemy connection | `make verify`: engine connects to expected database | Pass |
| Local credentials | Generated local passwords in ignored .env, file mode 0600 | Pass |
| GitHub authentication | `gh auth status` with network access confirms karthikeyansett1 | Pass |

The first Python download failed under restricted network access; retry with
approved network access succeeded. No claims have been downloaded or analyzed.
Live database checks now pass as well as Compose syntax validation.
The initial sandbox blocked Docker and local TCP access; approved access allowed
verification. A live test caught SQLAlchemy expecting `username` rather than
`user`; corrected the mapping and included this connection check in `make verify`.

## Next actions

1. Review this checkpoint together.
2. Decide whether to push Step 0 to GitHub. Only an explicit yes authorizes it.
3. Before an approved push, verify GitHub authentication and repository destination.
4. Continue with Step 1 data acquisition after the checkpoint review.

No LLM API key or paid API usage is needed at this stage. Provider credentials
and a spending limit will be handled before the AI assistant checkpoint.

Proposed commit: `Step 0: project skeleton, Python env, Postgres via Docker Compose`.

## User review and publication

User review: user approved publishing Step 0.
Push decision: user explicitly said “yes push to github”. Applies to Step 0 only.
Publication target: https://github.com/karthikeyansett1/medicare-claims (public), main branch.
The actual published commit is verifiable in GitHub history.
