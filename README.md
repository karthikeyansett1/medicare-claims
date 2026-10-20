# Medicare Provider Performance Analytics

A reproducible claims warehouse and analytics application exploring how patient attribution changes provider spending comparisons. Built with **Python, PostgreSQL, dbt, Streamlit, sqlglot, Docker and GitHub Actions** using CMS synthetic Medicare data.

**[Open dashboard](https://karthikeyansett1-medicare-provider-performance.static.hf.space/index.html)** · **[Live AI demo](https://karthikeyans-afjcffkdltc8rije9i7upq.streamlit.app/)** · **[Project guide](docs/project_guide.md)** · **[PDF guide](docs/Medicare_Analytics_Interview_Guide.pdf)** · **[Word guide](docs/Medicare_Analytics_Interview_Guide.docx)**

The dashboard is public and requires no installation. The live assistant requires a private access code from the project owner and queries a separate 1,000-member fixture. Dashboard views use the full Samples 1 and 2 aggregates; live answers should not be compared directly with full-population charts.

## Results

| Area | Result |
| --- | --- |
| Source data | 23,004,945 raw rows; 232,747 synthetic members; 2008–2010 |
| Reconciliation | 205 full-data checks: 151 silver and 54 gold |
| Financial completeness | $41.335M of professional payments retained despite missing HCPCS codes |
| Attribution sensitivity | 35.2%–52.4% of common qualifying providers moved at least three medical-PMPM deciles |
| Readmissions | 3,233 among 49,998 eligible index episodes, before attribution |
| Assistant evaluation | 39/50 baseline; 49/50 in each of three final fixed-set runs |

Raw rows include beneficiary records, claim segments and drug events, not distinct medical claims. The assistant's 98% result is regression performance on reused cases, not accuracy on unseen questions. Independent human answer review remains pending.

## Architecture

![Data pipeline from source files through warehouse layers to analytics](docs/img/interview_pipeline.png)

- **Ingestion:** Python source validation, profiling and atomic PostgreSQL loading.
- **Warehouse:** dbt bronze/silver/gold layers with sample-aware keys, explicit table grains and reconciliation.
- **Analytics:** member attribution, exposure-normalized spending and utilization, observed readmissions, AHRQ CCS inpatient grouping and descriptive cost adjustment.
- **Presentation:** static full-data dashboard and a separate access-controlled Streamlit SQL assistant.
- **Validation:** isolated Docker fixture build, dbt tests, independent SQL checks and GitHub Actions.

[Measure definitions](assistant/measure_definitions.md) · [Methodology](docs/methodology_memo.md) · [Data provenance](docs/data_sources.md) · [Architecture decisions](docs/decisions.md)

## Main finding

Assigning members by office-visit plurality or by professional allowed cost produces different provider panels. Both the composition of a panel and its comparison population affect its cost rank.

| Sample / year | Common providers | PMPM Spearman | Moved ≥3 deciles |
| --- | ---: | ---: | ---: |
| 1 / 2009 | 105 | 0.412 | 37 (35.2%) |
| 1 / 2010 | 82 | 0.017 | 42 (51.2%) |
| 2 / 2009 | 117 | 0.353 | 43 (36.8%) |
| 2 / 2010 | 84 | 0.055 | 44 (52.4%) |

Comparisons use panels with at least 20 members; ranks are assigned before intersecting provider cohorts. These synthetic results illustrate methodology sensitivity, not real provider quality. [Detailed findings](analysis/findings.md).

## Run locally

```sh
git clone https://github.com/karthikeyansett1/medicare-claims.git
cd medicare-claims
make setup
make dashboard
```

The local dashboard reads committed aggregate/provider extracts and does not require a warehouse or API key. Python 3.11 and dependency downloads are required.

For an isolated 1,000-member engineering build with Docker:

```sh
docker compose --env-file /dev/null -p medicare-fixture-ci \
  -f compose.ci.yml up --build --abort-on-container-exit --exit-code-from pipeline
```

Use a new Compose project name for a fresh cluster. To reproduce the full data pipeline, configure `.env` from `.env.example`, then run `make all` and the reconciliation targets documented in the [build guide](docs/full_project_walkthrough.md). Source downloads/extraction occupy about 7 GB, with additional database storage. Never commit credentials or run fixture loading against the full warehouse.

## Live assistant

![Guarded assistant request path](docs/img/interview_assistant.png)

The assistant uses shared measure definitions, SQL AST validation, seven allowlisted tables, a read-only query role and execution limits. A separate PostgreSQL role reserves a conservative cost before each model call against a shared $5 lifetime allowance. Page views and saved examples make no model calls. Runtime cannot reset the allowance. [Deployment and controls](https://github.com/karthikeyansett1/medicare-claims/blob/codex/live-assistant-cloud/deployment/live/README.md).

The 50-question evaluation contains 45 reference SQL cases and five clarification cases. The final three runs each achieved 49/50 strict agreement. Evaluation limits, failure analysis and accounting remain available in the [evaluation report](eval/results/summary.md).

## Limitations

- Data are synthetic; annual enrollment counts are exposure proxies rather than verified continuous coverage.
- Medical payments exclude prescription gross cost. Allowed amounts and paid amounts serve different purposes.
- Expected cost is a descriptive 2008 model fit, not an untouched prospective evaluation. Readmission rates are observed and not risk-adjusted.
- Conditions summarize principal-diagnosis inpatient spending; they are not total medical cost by condition.
- SQL permissions and passing tests do not guarantee correct AI reasoning. Independent human review is still outstanding.

## Documentation

Start with the [concise illustrated project guide](docs/project_guide.md). The [documentation index](docs/README.md) separates methodology, reproduction and supporting evidence. Reviewers can use the [answer review checklist](docs/human_review_checklist.md) without making paid API calls.
