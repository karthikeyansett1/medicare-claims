# Provider Performance Analytics on Medicare Claims

Build a reproducible warehouse of synthetic Medicare claims to compare provider
cost, utilization, and readmission rankings under two attribution methods.
Later checkpoints add a dashboard and an evaluated analytics assistant.

**Status: Step 0 local setup verified; GitHub publication approved.
No claims loaded; no results measured.**

## Work checkpoint by checkpoint

Each step includes implementation, verification evidence, and notes covering
what we did, why it matters, and how to explain it in an interview. We review
that checkpoint together before continuing. GitHub pushes require an explicit
yes for that specific step. Step 0 publication is approved. Repository: https://github.com/karthikeyansett1/medicare-claims.
Future pushes still require separate approval.

See [the roadmap](docs/roadmap.md), [Step 0 notes](docs/steps/00-setup.md),
and [the decision log](docs/decisions.md).

## Local setup

From this folder, with Docker Desktop running and uv installed:

```sh
cp .env.example .env
# Edit PG_PASSWORD in .env. Do not put real credentials in .env.example.
make setup
make db-up
make verify
```

Python 3.11 and dependencies must download successfully before setup is complete.
PostgreSQL is bound to localhost. Connection helpers load .env relative to the
project root, and existing environment variables take precedence.

The full `make all` pipeline will be added as its stages are implemented.
GitHub authentication is needed only for publication, not local development.
The local folder remains `Project 3`; the proposed GitHub name is `medicare-claims`.
