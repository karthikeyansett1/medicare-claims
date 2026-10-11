# Step 10 — provider cost, utilization and descriptive risk adjustment

## What we did and why

Built one provider/sample/year/method mart from independently aggregated member-year costs, merged admissions, and Step 9 readmissions. Kept medical Medicare paid separate from Rx gross cost and annualized utilization with exposure months. This prevents joined event tables from multiplying payments. Kept every panel but ranked only those with at least 20 members.

Fit an exposure-weighted positive conditional-mean GLM using 2008 data and fixed alpha=1. Coefficients/configuration and diagnostics are JSON. Refresh predictions in one transaction; rebuild the mart afterward. No secrets or individual prediction exports enter Git.

## Verification

- `make metrics`: one model, eight data tests and one dbt unit test passed. The fixture covers 20-member threshold, partial-year exposure and multiple episodes without multiplying costs.
- `make verify-metrics`: 161,870 panels and 2,267,884 independently calculated numeric/ranking comparisons; 426 panels qualify (2009 A/B:121/117, 2010 A/B:84/104).
- `RUN_DB_TESTS=1 .venv/bin/python -m pytest tests/ -q`: 42 passed.
- SQLFluff: new mart passes PostgreSQL dbt-templated lint.
- Dependency lock preserved all earlier package versions; NumPy made explicit and scikit-learn plus dependencies added.

## Temporal development diagnostics

Fit includes 73,260 nonnegative eligible 2008 member-years; one negative outcome (-$360 annual) is excluded only from fitting. Evaluation retains all 73,261 training-year and all 2009/10 outcomes, including adjustments. There are 136,037 application predictions.

| Year | Model weighted RMSE PMPM | Mean baseline RMSE | Observed medical paid | Expected medical paid |
|---|---:|---:|---:|---:|
| 2009 | 680.21 | 742.10 | $347,863,930.00 | $382,832,123.47 |
| 2010 | 484.84 | 527.26 | $179,083,020.00 | $205,525,866.40 |

The model improves this development error metric but overpredicts aggregate costs (~10% in 2009, ~15% in 2010). It is not clinically validated. Earlier linear and log-smearing attempts had structural negative-prediction/calibration problems and were rejected; future-year diagnostics had already been inspected, so these are not untouched validation results. No hyperparameter was tuned against future-year results. All final predictions are positive without flooring. Annual chronic flags are concurrent; this is descriptive adjustment, not forecasting or a causal quality score.

## How to explain it if asked

“I used member months rather than member counts to make utilization comparable when annual exposure differs. I aggregated each fact before joining so a member with several admissions could not multiply their payments. I compared raw PMPM with a positive expected-cost model, exposed calibration error, and only ranked panels meeting the reporting threshold. The data and enrollment measures are synthetic proxies, so I do not claim clinical validity.”

## Reproduce and inspect

On an existing core: `make metrics verify-metrics`. Fresh warehouse: after source preparation and bronze loading, `make pipeline-build` builds core dbt, fits risk, then builds the dependent mart. The model fails rather than inventing results if fewer than 31 training rows are available; small CI fixtures must satisfy this or test upstream/unit models separately. Source tests are excluded from core and run after prediction publication.

Artifacts: [numeric verification](../metrics_verification.json), [model coefficients and diagnostics](../../analysis/risk_model_diagnostics.json), [definitions](../measure_definitions.md).

Implementation reference: [scikit-learn PoissonRegressor](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.PoissonRegressor.html). Its log link ensures positive means; quasi-likelihood use does not claim continuous dollar outcomes are Poisson counts.

Publication: locally verified; commit and push pending parent checkpoint review.

## Publication

Published in [draft PR #10](https://github.com/karthikeyansett1/medicare-claims/pull/10)
from `codex/step-10-metrics`, based on `codex/step-09-readmissions`,
under standing authorization to commit and push each verified checkpoint.
Earlier draft PRs remain unmerged.
