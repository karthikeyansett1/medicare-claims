# How much does attribution change provider rankings?

## Question and data

How sensitive are provider cost and readmission rankings to the rule assigning members to providers? This project compares two retrospective rules while holding financial definitions and eligibility policies constant. It demonstrates a reproducible analytic workflow, not which providers deliver better care.

CMS DE-SynPUF Samples 1 and 2 contain **232,747 sample-aware synthetic members** and **23,004,945 raw rows** across sixteen files for 2008–2010. Raw rows include annual beneficiary records, claim segments and drug events; they are not 23 million distinct medical claims. Performance years 2009/2010 contain **272,105 eligible member-years** across four sample/year cohorts. A person can contribute more than once across years.

CMS cautions that “no beneficiary in the DE-SynPUF is an actual Medicare beneficiary.” Its synthesis alters relationships between variables, limiting population inference ([CMS user manual, p. 1](https://www.cms.gov/research-statistics-data-and-systems/downloadable-public-use-files/synpufs/downloads/synpuf_dug.pdf)). Sample 1's unavailable 2010 source was recovered from an archived CMS ZIP with identity and integrity checks; [provenance](data_sources.md) records that exception.

## Definitions

Eligibility uses annual Part A/B enrollment counts, zero HMO months and a death-adjusted required-month count. This FFS screen cannot prove continuous or overlapping monthly coverage. All identities include sample; unattributed member-years remain explicit. Provider reporting requires at least 20 attributed eligible members per sample/year/method; thresholds 10 and 30 are sensitivity checks.

**Method A** selects the rendering NPI with the most distinct office E&M claim-from dates (99201–99205, 99211–99215), breaking ties by latest office date, then lowest text NPI. **Method B** selects the largest known allowed-amount sum over all professional lines, breaking ties by distinct professional service dates, then lowest text NPI. Unknown amounts are omitted and counted; all-unknown candidates cannot win. Known zero/negative amounts remain valid. Neither method establishes specialty or provider identity.

**Medical PMPM** is inpatient, outpatient and professional Medicare paid divided by attributed member-months. It includes members' services regardless of rendering provider. Prescription gross cost is separate; allowed charges are not paid amounts. Admissions and ED annualized rates divide event counts by member-months and multiply by 12,000. ED uses an outpatient HCPCS proxy; dates, enrollment and episodes remain claims-based approximations.

**Readmissions** merge overlapping inpatient intervals and same-day transfers. An eligible index counts as a readmission when its next dated admission occurs 1–30 days after discharge; indices use discharge year, and chained readmissions may also be indices. Missing/invalid dates, conflicting current/next headers, death through follow-up, insufficient annual FFS proxies and incomplete observation exclude indices. December 1, 2010 has 30 days available; December 2 does not. There is no planned-readmission exclusion or readmission risk adjustment.

**Cost adjustment** fits an exposure-weighted positive log-link GLM on eligible 2008 records using age, sex and eleven concurrent chronic flags. Provider O/E divides observed medical payment by summed expected payment. This adjusts cost only. Principal-diagnosis AHRQ CCS assigns inpatient payment once; the conditions mart pools samples and is not a sample-specific or total-medical-cost view. [Canonical definitions](../assistant/measure_definitions.md) specify all boundaries and missing-value policies.

## Findings

The [comparison exports and charts](../analysis/findings.md) support five conclusions:

1. **35.2%–52.4%** of providers common to the two qualifying cohorts moved at least three medical-PMPM deciles. The four common cohorts contain **105, 82, 117 and 84 providers**, respectively (Sample 1/2009, 1/2010, 2/2009, 2/2010). These are separate reference populations, not one pooled provider ranking.
2. **0.017–0.412** was the across-method medical-PMPM Spearman range. Deciles are assigned within each qualifying method population before intersection; Spearman uses common-cohort raw scores with average ranks for ties. Deterministic NPI tie breaks can split equal costs across operational deciles.
3. **85.9%–88.0%** of jointly attributed members changed provider. Method A covered **72.1%–78.8%** of all eligible members; B covered **82.3%–86.4%**. Reassignment and coverage use different denominators.
4. **10 to 1** was the largest absolute PMPM-decile movement: synthetic NPI `2639271506`, Sample 2/2009, changed from **$730.95 to $329.42 PMPM**. Its A/B panels contained 21/26 members but only two retained members: 19 left and 24 entered. This explains a cohort-composition change, not clinical improvement.
5. **1.103 and 1.160** were aggregate expected/observed payment ratios in 2009 and 2010. Overprediction limits interpretation of adjusted ranks; raw-versus-O/E rank correlation ranged **0.527–0.769** across the eight method cohorts.

## Exclusion waterfall

The audit starts with **128,814 merged or excluded episodes**, including 2008 and out-of-window episodes. First-applicable exclusions remove 183 header conflicts, 51,868 discharges outside performance years, three deaths on/before discharge, 585 incomplete data windows, 99 deaths during follow-up, 25,738 index FFS failures and 340 follow-up FFS failures. The earlier invalid-date stages remove zero episodes. **49,998 eligible indices** remain, with **3,233 readmissions (6.47%)** before provider attribution. This denominator is episodes, not members or reportable-provider panels. [Independent verification](readmission_verification.json) preserves the counts; the [waterfall chart](../analysis/output/readmission_waterfall.png) separates samples.

## AI assistant evaluation

**DEFERRED: model accuracy has not been measured.** The 50 held-out cases comprise 45 executable gold queries and five clarification cases. Offline gold execution validates the harness, not generated SQL or answer accuracy. Prior live attempts encountered exhausted API credits; no paid calls are authorized until funding and renewed authorization. Execution accuracy, v1/v2 improvement, failure-type results, three-run variance and 15-answer human faithfulness review remain pending in the [evaluation status table](../eval/results/summary.md). SQL guardrails and a read-only database role are implementation safeguards, not evidence of analytic correctness.

## Limitations and the real-data version

Synthetic relationships, inferred transfers, no planned-readmission exclusion, unknown specialty and annual enrollment proxies prevent clinical conclusions. Small readmission denominators remain unstable despite the 20-member panel threshold. The cost model uses concurrent features and overlapping people across years; 2009/2010 diagnostics informed development, so those years are not untouched validation or a prospective forecast.

With real data, the next design would verify monthly enrollment and clinical episode rules, validate appropriate HCC or other risk adjustment, compare specialty-aware and prospective attribution, and quantify reliability with uncertainty intervals and shrinkage before comparing providers. A temporal holdout would remain untouched during model selection. These are future requirements, not implemented capabilities.

*Validation scope: results are supported by the linked reconciliation and evaluation artifacts. Independent human answer review and clinical validation have not been completed.*
