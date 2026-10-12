# Attribution sensitivity — measured findings

Samples 1, 2, performance years 2009 and 2010. All figures describe synthetic
data. Each sample/year has its own ranking population. Provider identifiers are
synthetic and do not establish real provider identity or specialty. The default
panel threshold is 20 attributed eligible member-years.

## Coverage and reassignment

Coverage uses all eligible members; reassignment uses only members attributed
under both methods. Method A uses office-visit plurality; Method B uses
professional allowed amounts.

| Sample | Year | Eligible | Coverage A | Coverage B | Reassigned / jointly attributed |
| --- | --- | ---: | ---: | ---: | ---: |
| 1 | 2009 | 72,692 | 78.8% | 86.4% | 50,366 / 57,247 (88.0%) |
| 1 | 2010 | 63,345 | 72.4% | 82.5% | 39,381 / 45,834 (85.9%) |
| 2 | 2009 | 72,656 | 78.5% | 86.4% | 50,122 / 57,055 (87.8%) |
| 2 | 2010 | 63,412 | 72.1% | 82.3% | 39,338 / 45,698 (86.1%) |

## Medical PMPM ranking sensitivity

Deciles are calculated before intersecting the two qualifying provider cohorts.
Spearman uses common-cohort raw scores with average ranks for ties. High-cost
overlap is the common-cohort top-decile Jaccard. Operational deciles break ties
by synthetic NPI; these comparisons do not establish which method is better.

| Sample | Year | Common providers | Spearman | Moved ≥3 deciles | Top-decile Jaccard |
| --- | --- | ---: | ---: | ---: | ---: |
| 1 | 2009 | 105 | 0.412 | 37 (35.2%) | 12.5% |
| 1 | 2010 | 82 | 0.017 | 42 (51.2%) | 8.3% |
| 2 | 2009 | 117 | 0.353 | 43 (36.8%) | 17.6% |
| 2 | 2010 | 84 | 0.055 | 44 (52.4%) | 0.0% |

At panel thresholds 10/20/30, the population and reference distribution both
change. These ranges are sensitivity analyses, not confidence intervals.

| Sample | Year | PMPM Spearman at 10 / 20 / 30 | Common providers at 10 / 20 / 30 |
| --- | --- | --- | --- |
| 1 | 2009 | 0.252 / 0.412 / 0.414 | 187 / 105 / 79 |
| 1 | 2010 | 0.149 / 0.017 / 0.073 | 142 / 82 / 67 |
| 2 | 2009 | 0.334 / 0.353 / 0.469 | 178 / 117 / 83 |
| 2 | 2010 | 0.057 / 0.055 / 0.123 | 148 / 84 / 64 |

## Risk adjustment and readmissions

The expected-cost model is refit on eligible 2008 records from the selected samples.
It is a concurrent descriptive GLM, not a clinically validated causal model.
Raw PMPM and O/E can rank the same providers differently. A 20-member panel
also does not guarantee a reliable readmission rate; index stays can be sparse.

| Sample | Year | Raw vs O/E Spearman A / B | A/B readmission Spearman | Readmission common providers |
| --- | --- | ---: | ---: | ---: |
| 1 | 2009 | 0.612 / 0.527 | 0.267 | 105 |
| 1 | 2010 | 0.733 / 0.769 | 0.174 | 81 |
| 2 | 2009 | 0.621 / 0.632 | 0.173 | 117 |
| 2 | 2010 | 0.692 / 0.706 | 0.272 | 83 |

Aggregate model calibration across the selected samples: 2009: expected/observed paid 1.103; 2010: expected/observed paid 1.160. This calibration limitation is another reason not to treat adjusted rankings as clinical quality.

Across the selected samples and all audit years, ordered exclusions retain **49,998 of 128,814 episodes**. The waterfall intentionally includes 2008 and out-of-window episodes.

## Why the largest global mover changed

Synthetic NPI **`2639271506`**, Sample **2**, **2009**, is the current largest absolute PMPM-decile mover across the selected samples. Ties use absolute rank movement, then sample/year/NPI. It moves from decile **10 to 1**, rank **119/130 to 12/129**, and PMPM **$730.95 to $329.42**.

The A panel has **21 members** and B has **26**: **2 retained**, **19 outgoing**, and **24 incoming**. Cohort replacement changes spending and exposure even when panel sizes look similar.

| Cohort | Members | Member-months | Medical paid |
| --- | ---: | ---: | ---: |
| incoming_B_only | 24 | 288 | $93,960.00 |
| outgoing_A_only | 19 | 228 | $175,380.00 |
| retained | 2 | 24 | $8,820.00 |

| Medical paid component | Outgoing A-only | Incoming B-only | Incoming − outgoing |
| --- | ---: | ---: | ---: |
| Inpatient | $33,000.00 | $25,000.00 | $-8,000.00 |
| Outpatient | $84,930.00 | $35,040.00 | $-49,890.00 |
| Professional | $57,450.00 | $33,920.00 | $-23,530.00 |
| Total | $175,380.00 | $93,960.00 | $-81,420.00 |

This is a cohort-composition explanation, not evidence of clinical cause or
services delivered by the attributed provider. Medical PMPM includes all
attributed members’ medical services regardless of rendering provider and
excludes Rx gross cost. The professional-service export reports HCPCS-level
paid and allowed amounts without member identifiers; those amounts are not
interchangeable. No diagnosis, specialty or clinical narrative is inferred.

## Inspect and reproduce

Run `make compare verify-comparison` after `make pipeline-build`. See the
[combined integration evidence](../docs/steps/11b-sample2.md) and
[comparison policy](../docs/steps/11-comparison.md). Historical Sample 1 findings
are retained in `docs/checkpoints/sample_1/analysis/`.

- [Aggregate comparisons](output/method_comparison.csv)
- [Provider pairs](output/provider_comparison.csv)
- [Mover cohorts](output/mover_cohorts.csv)
- [Mover services](output/mover_services.csv)
- [Independent verification](output/verification.json)

![PMPM rank comparison](output/pmpm_rank_scatter.png)
![Absolute decile movements](output/decile_movement.png)
![Ordered readmission exclusions](output/readmission_waterfall.png)
