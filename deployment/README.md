# Deployment and cost controls

The public application is a free **static Hugging Face Space**:
[Open Atlas](https://karthikeyansett1-medicare-provider-performance.static.hf.space) · [Space repository](https://huggingface.co/spaces/karthikeyansett1/medicare-provider-performance).

The four interactive dashboard pages use full Samples 1 and 2 provider/aggregate exports. The Assistant demo displays four saved aggregate query results, verified using a dedicated read-only Neon role against the deterministic 1,000-member Sample 1 CI fixture. It neither queries Neon from the browser nor generates AI answers. No member/claim identifiers, database URLs, API keys, or raw files are shipped.

## Reproduce the public bundle

From repository root:

```sh
.venv/bin/python deployment/build_static.py /tmp/medicare-hf-static
.venv/bin/python -m pytest tests/test_deployment.py
```

The builder checks committed dashboard hashes and copies an exact six-file allowlist. Upload only that output directory to the existing static Space. Its README metadata is separate from the GitHub README. The public app uses no external JavaScript libraries and makes only a same-origin data.json request.

`publish_database.py` is an owner-only initial deployment tool: it refuses any nonempty destination or preexisting demo role, reads DEPLOY_DATABASE_URL from ignored `.env`, copies only seven approved tables from the isolated fixture container, compares every serialized CSV byte, and creates `medicare_demo_ro`. It stores the generated DSN only in mode-600 `.env` as DEPLOY_ASSISTANT_DATABASE_URL. Do not rerun against the populated database. `export_examples.py` can refresh the four fixed queries using that read-only DSN; never pass arbitrary question text or SQL to it. The admin DSN never belongs in any application runtime.

## Why static, and why a fixture?

On 2026-10-13 the account's `isPro` was false, and a CPU Basic Docker creation attempt returned HTTP 402 requiring PRO. No subscription or hardware upgrade was purchased; unrelated existing Spaces were untouched. [Current HF documentation](https://huggingface.co/docs/hub/spaces-overview) distinguishes free static Spaces from paid-plan eligibility for creating compute Spaces. This replaces the guide's outdated Streamlit SDK instruction. CPU Basic's zero hourly price does not remove the account subscription requirement.

The seven full warehouse tables total **922,353,664 bytes** before additional database overhead. [Neon's plans documentation](https://neon.com/docs/introduction/plans) states 0.5 GB/project, while its newer [free-plan announcement](https://neon.com/blog/neon-free-plan-1-gb-per-project) describes 1 GB. Rather than relying on the larger limit without project confirmation, the hosted fixture occupies **17,588,224 database bytes** with ample headroom under either. Full-data dashboard exports remain separate. `database_manifest.json` records exact table counts and serialized hashes. Neon compute/transfer quotas still apply to owner refreshes; public static visits incur no database query load.

## Optional Docker demo

```sh
.venv/bin/python deployment/build_docker.py /tmp/medicare-hf-docker
docker build --platform linux/amd64 -t medicare-demo /tmp/medicare-hf-docker
docker run --rm -p 7860:7860 medicare-demo
```

The separate Docker README uses sdk docker and app_port 7860. The image runs unprivileged, uses a Linux AMD64 Python 3.12 dependency lock, and contains only Streamlit dashboard/demo dependencies and allowlisted runtime files. It needs no secrets. The optional image was built and independently checked as Linux AMD64, running as the unprivileged `user` with `ENABLE_LIVE_ASSISTANT=false`. Its dashboard was checked using AppTest with container networking disabled. It is not deployed to Hugging Face; the public deployment remains static. HF's documented outbound ports are 80, 443 and 8080; validate hosted PostgreSQL connectivity before offering a future live database feature. Do not assume port 5432 works.

## Future live activation — owner action required

Funded owner-run evaluation is separate from public service activation. The original local `Agent` implementation is preserved, but both the public bundle and optional Docker demo omit that callable backend. Local `make assistant` defaults to the static demo; with explicit owner authorization, the owner can set `ENABLE_LIVE_ASSISTANT=true` in the server environment, provide `LLM_API_KEY`, and use an `ASSISTANT_DATABASE_URL` containing only the read-only role. Export the switch into the process environment (for example `ENABLE_LIVE_ASSISTANT=true make assistant`); the UI does not read that switch from `.env`. Run smoke/evaluation before claiming accuracy. The public static site cannot be switched into live AI by a visitor or environment flag; activating live service requires an explicit new server deployment.

The existing local assistant allows 10 submitted questions/session, 6 reserved calls/minute, 60/day and 1,000,000 reserved tokens/day by default. These are server environment limits, not public browser controls. Failed calls still consume reservations. Its SQLite budget store is persistent only within its local filesystem; ephemeral hosting restart or multiple replicas can reset or split the limit. Before a public live launch, use a shared durable quota store, owner-controlled authentication/access, and independently enforce hard provider/external spending bounds. A provider budget alert alone may not be a hard spending stop. Never treat browser session limits or ephemeral SQLite as a global spend guarantee.
