# Interview preparation

Start with the [illustrated project guide](project_guide.md) for a concise explanation. These additional questions cover implementation details and measurement tradeoffs.

## A short opening

“This project asks how much provider rankings change when the attribution rule changes. It processes 23.0 million raw rows for 232,747 synthetic Medicare members through PostgreSQL, dbt and Python. I compared office-visit plurality with professional allowed-amount attribution while keeping cost definitions and eligibility rules fixed. Across four sample/year cohorts, 35%–52% of common qualifying providers moved at least three medical-PMPM deciles. The useful result is sensitivity to methodology and panel composition, not evidence that a real provider delivers better care. The project also implements a dashboard and a guarded analytics assistant; the assistant scored 49/50 in each of three reused-set regression runs; this is not held-out accuracy.”

## What, why and how across the project

| Part | What and why | How to explain the implementation |
| --- | --- | --- |
| Sources and profiling | Make provenance and data defects visible before analysis. | Verify source sample identities and hashes; profile 16 files across Samples 1/2 and 2008–2010. Document the archived-source recovery. Raw rows include annual beneficiary records, claim segments and drug events. |
| Bronze, silver and gold | Preserve raw evidence, then establish reliable types and grains. | Atomic PostgreSQL loading; dbt typing, carrier-slot unpivoting and sample-aware keys. Reconcile money and counts independently. Retain paid professional lines without HCPCS: dropping them would lose $41,335,020. Full-data silver/gold verification passed 151 + 54 checks. |
| Eligibility and attribution | Compare two panel-building rules consistently. | Use annual A/B enrollment, zero HMO months and death-adjusted exposure as an FFS proxy. Keep unattributed members explicit. Compute A/B per sample/member/year, then report panels with at least 20 members; inspect thresholds 10 and 30. |
| Measures and CCS | Prevent numerator, denominator and join errors. | Sum medical paid at member-year grain; divide by attributed member-months. Merge inpatient episodes before readmissions. Allocate inpatient payment once using principal-diagnosis ICD-9 CCS, retaining UNMAPPED; any-diagnosis categories overlap and are not additive. |
| Cost adjustment | Check whether accounting for observed case mix changes cost rankings. | Fit an exposure-weighted positive log-link GLM on eligible 2008 records using age, sex and 11 concurrent chronic flags; provider O/E is observed divided by summed expected medical paid. This adjusts cost, not readmissions. |
| Comparison and dashboard | Make methodology effects inspectable. | Compare sample/year cohorts separately; expose four dashboard views: overview, scorecard, method comparison and conditions. Conditions pool samples and cover inpatient payment only. Trace the largest mover through retained, outgoing and incoming members. |
| Assistant and evaluation | Make SQL inspectable and enforce execution boundaries. | Provide schema, grains, definitions and eight training examples; generate a structured SQL plan, validate, execute read-only and explain actual rows. Permit one repair. Keep 50 evaluation cases separate; 45 gold queries executed offline and five require clarification. No model accuracy is available. |
| Reproduction and delivery | Let another person verify engineering behavior. | Docker/GitHub Actions use an isolated 1,000-member fixture. The recorded database-enabled CI suite passed 133 Python tests, plus dbt and SQL lint. Full-data findings remain separate from fixture evidence; consult the README for current deployment status. |

## The guide's 11 interview questions

### 1. Why plurality of office visits for Method A? What are its weaknesses?

It is an interpretable proxy for a recurring outpatient relationship. Count distinct office E&M claim-from dates for HCPCS 99201–99205 and 99211–99215, rather than repeated lines. It misses relationships outside those codes, depends on coding completeness and can assign someone with very few visits. No specialty field means this is not proven primary-care attribution. Method B instead selects the rendering NPI with the largest known allowed-amount sum over all professional lines.

### 2. How did you handle ties, and does the tie-breaker change results?

A breaks visit-count ties by latest office date, then lowest text NPI. B breaks allowed-amount ties by distinct professional service dates, then lowest text NPI. Unknown allowed amounts are omitted and counted; all-unknown candidates cannot win, while known zero/negative values remain valid. These rules make results reproducible. Another rule could change tied assignments, but I have not isolated its effect quantitatively. Separately, ranking deciles use deterministic NPI tie breaks, so equal costs can land in different deciles.

### 3. Walk through readmission exclusions. Why exclude December 2010 discharges?

The denominator is eligible index episodes, not members. After date validation and episode merging, apply ordered exclusions for conflicting current/next headers, discharge outside 2009/2010, death on/before discharge, incomplete observation, death during follow-up and index/follow-up FFS failures. The numerator counts eligible indices whose next dated admission is 1–30 days after discharge; a readmission can itself become another index. Of 128,814 audit episodes, 49,998 indices remain with 3,233 readmissions (6.47%), before attribution. Do not exclude all December discharges: December 1, 2010 has 30 observable days through December 31; December 2 does not. There is no planned-readmission exclusion or readmission risk adjustment.

### 4. How did you identify transfers without a discharge-status code?

Merge overlapping intervals and admissions on the prior discharge date into one episode, using the running episode boundary to preserve chains. A same-day admission therefore does not count as a readmission. This is a transparent date-based approximation; I cannot establish whether the underlying event was a clinical transfer.

### 5. Why member-months instead of member counts for per-1,000 rates?

Exposure can differ, especially after death. Annualized admissions or ED events per 1,000 equal events / member-months × 12,000; medical PMPM equals medical paid / member-months. Counts alone treat partial and full years as equivalent. Annual enrollment fields do not prove continuous or overlapping monthly coverage, so the exposure is explicitly a proxy.

### 6. What is paid versus allowed, and which did you use where?

Medicare paid is the payment amount; allowed is the recognized charge basis and is not interchangeable with paid. Method B uses professional allowed amounts to choose a provider. Medical PMPM uses inpatient + outpatient + professional Medicare paid for all attributed members' services, regardless of who rendered them. Prescription drug gross cost stays separate because it is not a Medicare-paid field. Aggregate facts before joins to avoid multiplying dollars.

### 7. Why synthetic data, and what can and cannot be concluded?

CMS DE-SynPUF permits a public, reproducible demonstration without real beneficiary records. It supports testing pipelines and showing how definitions alter results. Synthesis changes relationships, so the magnitude here cannot establish real provider quality, patient outcomes or population effects. NPIs are synthetic; provider identity and specialty are unknown. The 232,747 members differ from the 272,105 eligible 2009/2010 member-years because people may contribute in both years.

### 8. What was the most common AI failure, and how did you fix it without overfitting?

The leading held-out failure category requires completed evaluation and review. Earlier API attempts exhausted credits; separately authorized funded local validation followed. Offline gold-query execution validates the harness, not generated SQL or narrative faithfulness. The implemented taxonomy covers methodology errors, but its counts, v1/v2 accuracy, three-run variance and 15-answer human review remain pending. For each authorized run, freeze v1 and the held-out set, inspect real failures, improve general definitions or separate training examples, then evaluate frozen v2. Never copy gold queries into runtime context.

### 9. Why no vector database?

The bounded seven-table schema, canonical definitions and examples fit in the prompt. Passing the full context avoids a retrieval step that might omit a needed definition. Retrieval becomes a design option if the domain outgrows that context; its value would need evaluation. Complete context still does not guarantee correct SQL.

### 10. A client says rankings changed after a methodology update. How would you investigate?

First freeze the source/build and reproduce both versions. Compare eligibility, exposure, attribution, financial fields, exclusions, panel thresholds and ranking populations separately. Reconcile member movement and dollars before interpreting ranks. Here, the largest mover, synthetic NPI 2639271506 in Sample 2/2009, went from decile 10 to 1 and $730.95 to $329.42 PMPM. Its panels had 21 and 26 members, but only two stayed: 19 left and 24 entered. That is a concrete composition explanation, not clinical improvement. Deciles are formed within each qualifying method population before intersecting providers; the 35%–52% headline uses only the common qualifying providers.

### 11. What would change with real claims?

Verify monthly eligibility and clinically appropriate episode/planned-readmission rules; obtain provider identity and specialty; consider prospective attribution and validated risk adjustment such as an appropriate HCC model. Assess reliability with uncertainty intervals and shrinkage before comparing small panels. Reserve an untouched temporal holdout. Add data-access and privacy controls appropriate to the actual data and operating environment. These are future requirements, not delivered clinical capabilities.

## Likely follow-ups

- **Is the cost model prospective or clinically validated?** Neither. It uses concurrent annual flags; people can overlap across years, and 2009/2010 diagnostics informed development. Aggregate expected/observed paid was 1.103 in 2009 and 1.160 in 2010, showing overprediction. Continuous costs use a Poisson quasi-likelihood log-link model for positive means, not an assumption that costs are Poisson counts.
- **Why both SQL validation and a database role?** Defense in depth: AST checks enforce one allowed SELECT, approved tables/columns/functions and at most 500 rows. The role lacks write/create privileges, and execution adds a read-only transaction, timeouts and output caps. Explicit join syntax cannot prove correct join semantics; successful execution cannot prove analytic correctness.
- **What does “tested” mean?** Full-data silver/gold reconciliation: 205 checks. Historical Step 12 database-enabled suite: 114 tests. Later isolated CI: 133 Python tests including database tests. None is a model accuracy percentage. The 1,000-member fixture tests engineering behavior, not full-population estimates.
- **What can a recruiter try?** Use the current README's verified deployment link and mode. A static demo with predefined SQL/result cards demonstrates verified examples, not live LLM generation. Distinguish full-data dashboard extracts from the 1,000-member hosted fixture. The API integration exists, but paid live validation remains deferred until credits and renewed authorization.
- **Which attribution method is better?** This analysis does not establish that. It measures sensitivity under two stated rules. Choosing a rule requires the intended accountability relationship and validation beyond these synthetic records.

Evidence: [canonical definitions](../assistant/measure_definitions.md), [methodology memo](methodology_memo.md), [findings](../analysis/findings.md), [assistant boundaries](steps/12-assistant.md), [evaluation status](../eval/results/summary.md), [CI scope](steps/15-ci.md), [resume entry](resume_entry.md).
