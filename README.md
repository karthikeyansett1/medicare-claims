# Provider Performance Analytics on Medicare Claims

Changing member attribution moved **35%–52% of common providers at least three medical-PMPM deciles** in four synthetic Medicare cohorts.
This reproducible PostgreSQL/dbt/Python project follows the result from raw files through audited measures, an interactive dashboard and a guarded analytics assistant.

| Evidence | Current result |
| --- | --- |
| Source scope | **232,747 synthetic members**, Samples 1 and 2, 2008–2010 |
| Raw input | **23,004,945 rows**: beneficiary records, claim segments and drug events |
| Performance population | **272,105 eligible member-years**, 2009/2010 |
| Full-data reconciliation | **205 checks passed**: 151 silver + 54 gold |
| Latest full database suite | **156 passed**; deployment-head CI is recorded separately below |
| AI execution accuracy | **V1 39/50; v2 49/50 in each of 3 fixed-set runs** |

**Status:** the local pipeline, comparison analysis and four-page dashboard are implemented and verified. Live assistant validation/evaluation await API funding and renewed authorization; a free static public dashboard and verified SQL example demo are deployed (live AI remains disabled). Work is published as stacked draft PRs; earlier PRs are unmerged and `main` does not yet contain the complete build. [Roadmap](docs/roadmap.md) · [Methodology memo](docs/methodology_memo.md) · [Decision log](docs/decisions.md)

## Explore the dashboard

![Atlas provider dashboard overview](docs/img/dashboard-overview.jpg)

[Scorecard](docs/img/dashboard-scorecard.jpg) · [Method comparison](docs/img/dashboard-comparison.jpg) · [Conditions](docs/img/dashboard-conditions.jpg) · [Dashboard guide](docs/steps/14-dashboard.md)

After setup, `make dashboard` serves [the local dashboard](http://127.0.0.1:8502). Committed aggregate/provider extracts support all four pages without a database connection or API key. `make export` refreshes them from the warehouse. The local implementation is Streamlit. [Open the public interactive dashboard and Assistant demo](https://karthikeyansett1-medicare-provider-performance.static.hf.space) · [Hugging Face Space](https://huggingface.co/spaces/karthikeyansett1/medicare-provider-performance). The public static dashboard covers full Samples 1 and 2; its four example questions show saved SQL results verified against a separate 1,000-member fixture, not live AI. [Deployment scope and reproduction](deployment/README.md).

## Architecture

![Architecture from synthetic source files to audited analytics](docs/img/architecture.png)

[Editable SVG](docs/img/architecture.svg) · [Diagram generator](docs/render_architecture.py)

Python verifies source identities/hashes and loads PostgreSQL bronze atomically. dbt produces typed silver, sample-aware gold facts/dimensions, attribution, CCS and readmission models. A Python 2008 cost-model fit precedes the dependent provider mart. Comparisons and dashboard exports contain provider/aggregate data; the assistant queries only its allowlisted warehouse tables through a dedicated read-only role. Its live Responses API path remains unevaluated.

The canonical [measure definitions](assistant/measure_definitions.md) are shared by documentation, dashboard and assistant. An isolated Docker/GitHub Actions fixture pipeline checks the build without replacing full-data evidence or calling paid models. See [CI scope and isolation](docs/steps/15-ci.md).

![Historical dbt lineage through the gold layer](docs/img/step-05-dbt-lineage.jpg)

This actual dbt screenshot records the **historical Sample 1 Step 5 checkpoint**, before attribution and later marts. Generate current lineage with `make dbt-docs`; serve `dbt_project/target` locally to inspect the complete graph.

## Run it

Use the implementation branch while the stacked PRs await integration:

```sh
git clone --branch codex/step-17-deploy https://github.com/karthikeyansett1/medicare-claims.git
cd medicare-claims
```

**Dashboard only:** install uv (or Python 3.11), then run `make setup` and `make dashboard`. Dependency and dbt-package downloads need network access; no warehouse is needed to read the committed dashboard extracts.

**Full data:** with Docker Desktop running, copy `.env.example` to `.env` and configure local database credentials privately. Keep secrets out of Git. Then:

```sh
cp .env.example .env
# Edit .env locally before continuing.
make all
make verify-bronze verify-silver verify-gold
make verify-attribution verify-grouper verify-readmissions verify-metrics verify-comparison
make test-db
make dashboard
```

`make all` already runs `make setup`; `make setup && make all` is also valid but repeats installation. This is a long full build, not a quick demo: downloads/extracted sources alone occupy about 7 GB, with additional warehouse and runtime storage. It defaults to `MEDICARE_SAMPLES=1,2`, then downloads, profiles, loads, builds, fits expected cost, compares and exports sequentially. Source integrity and archive exceptions are documented in [data provenance](docs/data_sources.md). Run reconciliation after database builds finish.

**Small isolated build:** from a fresh clone, Docker can build the committed 1,000-member engineering fixture without downloading the full claims:

```sh
docker compose --env-file /dev/null -p medicare-fixture-ci \
  -f compose.ci.yml up --build --abort-on-container-exit --exit-code-from pipeline
```

Use a new Compose project name for each fresh cluster. This runs `make ci` inside an isolated runtime, including reconciliation, SQL lint and database tests. Direct `make ci` requires explicit settings for a fresh dedicated cluster and empty output directory; use the [CI instructions](docs/steps/15-ci.md). Fixture results are engineering evidence, not the full-data findings below.

**Assistant:** implementation and read-only setup are documented in [Step 12](docs/steps/12-assistant.md). The public demo makes no model calls. Funded local evaluation requires explicit owner authorization and spending limits. The [50-case harness](docs/steps/13-eval.md) has 45 gold queries and five clarification cases. The funded frozen-v1 baseline scored **39/50 (78%)** in execution/clarification comparison; [baseline evidence](eval/results/v1_2026-10-14_resumed/summary.json) is separate from offline gold validation. V2 scored **49/50 in each of three runs (98%–98%)**; see [completed evidence](eval/results/v2_2026-10-16_resumed/summary.json).

## What changed when attribution changed?

Medical-PMPM rankings compare providers with at least 20 members in each method. Deciles are assigned before intersecting cohorts; Spearman uses common-cohort raw scores and average ranks for ties.

| Sample / year | Common providers | PMPM Spearman | Moved ≥3 deciles |
| --- | ---: | ---: | ---: |
| 1 / 2009 | 105 | 0.412 | 37 (35.2%) |
| 1 / 2010 | 82 | 0.017 | 42 (51.2%) |
| 2 / 2009 | 117 | 0.353 | 43 (36.8%) |
| 2 / 2010 | 84 | 0.055 | 44 (52.4%) |

![Medical PMPM ranks under the two attribution methods](analysis/output/pmpm_rank_scatter.png)

Among members attributed by both rules, **85.9%–88.0% changed provider**. This uses a different denominator from coverage: Method A covers 72.1%–78.8% of all eligible members, versus 82.3%–86.4% for Method B. The largest mover's panel retained only two members while PMPM changed from $730.95 to $329.42, illustrating cohort replacement.

![Absolute PMPM decile movements across four cohorts](analysis/output/decile_movement.png)

Readmission exclusions retain **49,998 of 128,814 audit episodes** across both samples, with **3,233 readmissions (6.47%)** before attribution. The starting audit includes 2008 and out-of-window episodes; it is not a count of eligible performance-year admissions.

![Ordered readmission exclusion waterfall by sample](analysis/output/readmission_waterfall.png)

[Findings, denominator policies and downloadable tables](analysis/findings.md) · [Concise methodology memo](docs/methodology_memo.md)

## Limits and evidence

- Synthetic data support an engineering and methodology demonstration, not real provider ratings. Annual enrollment and claims-based event proxies cannot establish complete clinical observation or specialty.
- Cost adjustment uses concurrent features and a 2008 fit; later years informed development and are not untouched prospective validation. Readmissions are unadjusted, lack planned-readmission exclusions and may have sparse denominators. Conditions pool samples and describe principal-diagnosis inpatient spending only.
- Frozen v1 scored **39/50 (78%)** on the specified evaluation cases. V2 scored **49/50 in each of three runs** after inspecting v1 failures: a fixed-set regression, **not untouched held-out generalization**. Agent faithfulness review scored 15/15 for each version; independent human review remains pending. Offline SQL checks, guardrails and read-only permissions do not establish model correctness. See the [evaluation status](eval/results/summary.md).

The [roadmap](docs/roadmap.md) links checkpoint explanations and measured validation. Full-data evidence is in [silver reconciliation](docs/silver_reconciliation.json), [gold reconciliation](docs/gold_reconciliation.json), [Sample 2 integration](docs/steps/11b-sample2.md) and [dashboard verification](docs/steps/14-dashboard.md). The 129-test full-data dashboard checkpoint and newer 133-test isolated CI checkpoint have different dates and scopes; neither is an AI evaluation score. Historical Sample 1 artifacts are preserved in `docs/checkpoints/sample_1/`.

Step 15 is published in [draft PR #16](https://github.com/karthikeyansett1/medicare-claims/pull/16). At checkpoint `fc14ed9`, [push CI](https://github.com/karthikeyansett1/medicare-claims/actions/runs/38443340057) and [PR CI](https://github.com/karthikeyansett1/medicare-claims/actions/runs/38443347493) passed. `main` requires the `ci` check and an up-to-date branch; administrator enforcement is off. This does not imply the stacked PRs have merged or that future heads are already verified.

Documentation is agent-drafted from verified project artifacts; no independent human review is claimed. The owner should review and be able to explain the methodology before using it in interviews.

## Interview and resume materials

[Measured resume entry](docs/resume_entry.md) · [Interview preparation](docs/interview_prep.md) · [Step 17 deployment evidence](docs/steps/17-deploy.md). Public deployment does not establish AI accuracy; local evaluation evidence is reported separately.

Deployment is published in [draft PR #18](https://github.com/karthikeyansett1/medicare-claims/pull/18). Exact head `dfbe933` passed [push CI](https://github.com/karthikeyansett1/medicare-claims/actions/runs/38826989735) and [PR CI](https://github.com/karthikeyansett1/medicare-claims/actions/runs/38826995533). The public app stays static; stacked PRs remain unmerged.

Funded local validation used **$6.5081800** measured usage plus **$1.0315875** retained unknown reservations: **$7.5397675** against the $20 cap, including smoke and interrupted attempts. This is run accounting, not an invoice or account-wide balance. [Evaluation and review evidence](eval/results/summary.md).

The funded live runner is campaign-specific and intentionally rejects a fresh-clone or replacement ledger. A new paid campaign requires explicit owner setup, authorization and prior-spend accounting. Offline validation and the dashboard remain reproducible without paid access.
