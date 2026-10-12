# Financial and grain definitions

Canonical financial, attribution, readmission and provider measure definitions.
Source: historical synthetic CMS DE-SynPUF Samples 1 and 2, not identifiable patients
or verified real providers.

## Identity and grains

All member and provider keys include sample ID. Original member IDs and NPIs
remain text. Do not join facts on member_id alone after combining samples.
`dim_provider` covers observed rendering NPIs and canonical inpatient attending
NPIs. An E&M flag does not establish a primary care specialty or a real identity.

Facility facts have one row per sample/member/claim. They preserve the sum of
all source segments and retain silver's conflicting-header flags. The inpatient
name contains “stays” for continuity with the guide; the unit is still a
claim-based episode, not a clinically validated hospitalization.

`dim_member` takes demographics from the latest annual record and the earliest
nonblank death date across years. Historical state, sex, coverage, age, and chronic
flags remain in `dim_member_year`. Count of chronic conditions is NULL when any
of its eleven source flags is missing; unknown is not silently healthy.

## Calendar-year assignment

| Fact | Date assigning the entire event payment to a year |
| --- | --- |
| Professional line | Carrier claim-from date; no true line-level service date is provided here |
| Inpatient claim episode | Admission date on the lowest-numbered canonical segment |
| Outpatient claim | Earliest claim-from date across segments |
| Prescription event | PDE service/fill date |

This is event-year allocation, not prorated spending across service days. For
conflicting inpatient segments, the canonical admission year is an explicit
convention. Readmission eligibility must address those conflicts in Step 9.

The calendar includes observed pre-2008 dates. The 2008-2010 analysis-window flag
does not delete earlier claims. Costs without annual enrollment remain in the
summary with `has_annual_enrollment=false` and NULL `member_year_key`. Records without service dates use a NULL-year/`unknown` key bucket. Sample 1
has 278 such outpatient claims, retained across 147 member buckets.
Do not quietly exclude either bucket when reconciling warehouse money.

## Financial measures

`gold.fct_member_year_cost` is the canonical member-year aggregation:

- **medical_paid_amt** = inpatient_paid_amt + outpatient_paid_amt + professional_paid_amt.
  These are medical Medicare payments. Retain negative and equal-segment amounts.
- **professional_allowed_amt** is carrier allowed charges. It is separate from paid.
- **rx_gross_cost_amt** is gross prescription cost across payers. It is not
  Medicare-only paid and is not included in medical_paid_amt.
- **rx_patient_pay_amt** is prescription patient payment. It must not be added
  to gross drug cost as though it were a disjoint spending category.

Amounts use exact PostgreSQL NUMERIC. Each fact is aggregated independently by
sample/member/year before combination, preventing claim-to-claim fan-out.
Enrollment-only years have zero observed event counts and costs. Sums include
known amounts; missing-payment counters disclose unknown amounts rather than
claiming that every zero summary value is a known zero cost.

Detailed fact amounts remain available for drill-down and reconciliation.
Later provider metrics should aggregate this member-year summary after an
explicit attribution rule; do not reimplement its cost scope independently.

## Utilization and eligibility limits

Counts are professional slots, office E&M lines, inpatient claim episodes,
outpatient claims, ED-coded outpatient claims, and prescription events. These
are not interchangeable with unique visits, distinct days, or clinical admissions.
Office E&M uses the ten versioned 99201-99205/99211-99215 candidates. Outpatient
ED uses any segment's 99281-99285 HCPCS proxy, not revenue codes.

The annual FFS flags remain the documented Step 4 screening proxies. Annual
coverage counts cannot establish overlapping covered months or continuous
observation. Readmission denominator rules are specified in the linked Step 9 document.
`dim_dx_ccs` uses the verified AHRQ map with coverage checks from Step 8.

## Retrospective attribution (Step 7)

Population: eligible `dim_member_year` rows in 2009/2010, including explicit
unattributed rows for both methods. All grouping and joins use sample-aware
member-year identity. Claim-from date remains the professional service-day proxy.

- **A_visits:** rendering NPI with the most distinct office E&M dates; ties use
  the latest office date, then lowest text NPI. Multiple lines on one date count once.
- **B_allowed:** rendering NPI with the largest sum of known allowed amounts
  across all professional lines; ties use the most distinct service dates across
  those professional lines, then lowest text NPI. Missing amounts are excluded
  from the sum and counted explicitly; an all-unknown candidate cannot win B.
  A known zero or negative amount remains a valid observation. A partially known
  sum is incomplete and may bias assignment; winner missing counters expose this.

`attribution_candidates` retains every eligible member-year/NPI candidate and
its counts, dates, known amounts, and missing counts. Winner tables retain candidate
counts and counts tied on the primary score and on both ranking scores. The
union has exactly two rows per eligible member year, one per method. NULL NPI
means no qualifying candidate; it does not remove that person from coverage.
These rules do not infer provider specialty, primary care, or real provider identity.

Provider reporting requires at least 20 attributed members per sample/NPI/year/
method. Attribution itself retains small panels; reporting thresholds do not
change assignments. Later sensitivity analysis will compare thresholds 10 and 30.

## Readmissions (Step 9)

The detailed specification below was written before its Step 9 SQL implementation.

## Provider cost and utilization (Step 10)

Grain is sample, synthetic attributed NPI, performance year (2009/2010), method.
Sum required_months over attributed FFS-eligible annual records (12 for full year,
death-month adjusted otherwise). This is an annual-count exposure proxy, not
verified continuous coverage. Each member appears once per method/year; totals
must never be summed across attribution methods.

Medical Medicare-paid PMPM = (inpatient + outpatient + professional paid) / member
months. Preserve negative adjustments. Rx gross PMPM = PDE gross drug cost /
member months, separately; gross drug cost is not Medicare-paid Rx. No combined
Medicare-paid total or misleading pharmacy-paid share is produced.

Admissions count merged dated episodes by admission year, including header-conflict
episodes as utilization proxies. Invalid dates cannot be assigned and are excluded
from this dated rate; retained source money remains in its existing cost bucket.
ED counts outpatient claim proxies with project-defined ED HCPCS 99281–99285, not proven unique
ED encounters. Admissions and ED annualized rates = events / member months * 12,000.
Readmission numerator/denominator use Step 9 discharge year and exclusions.
Zero denominators yield NULL; independent member-year aggregation prevents fanout.

Panels of at least 20 members receive ranks and NTILE(10) deciles within sample,
year and method, ascending medical PMPM or observed/expected medical paid.
NPI breaks ties deterministically (including across decile boundaries); equal cost
does not imply equal rank. With fewer than ten qualifying providers NTILE uses
only the first N buckets. Small panels remain auditable with NULL ranks.
O/E requires complete member predictions; model failure blocks publication.

Risk features are age bands under65/65–74/75–84/85+, sex, and 11 concurrent annual
chronic flags, each with explicit unknown handling. Fit positive conditional mean
PMPM with exposure-weighted Poisson quasi-likelihood, log link and fixed L2 alpha=1
on 2008 eligible member-years. This is a loss/link choice for continuous costs,
not an assumption that dollar costs follow a Poisson distribution. One negative
2008 member-year is excluded from fitting and explicitly counted; observed costs
and all evaluation rows remain unchanged. Expected paid = exp(linear predictor)
* required_months. No prediction floor, outcome clipping, or unsafe pickle.

Earlier linear predictions were materially negative and global log-smearing
miscalibrated costs; they were rejected on structural grounds. Subsequent 2009/10
results are development temporal diagnostics, not untouched validation. Annual
features are concurrent, populations overlap across years, and synthetic source
patterns limit generalization. This is descriptive adjustment, not a clinical
risk score, causal provider effect, or prospective forecast.

# Measure specification: 30-day all-cause readmission

Written before implementation of Step 9.
This is a descriptive measure of historical synthetic DE-SynPUF claims, not an
endorsed CMS quality measure or evidence about real patients/providers.

## Episode construction and audit population

Partition by sample-aware member identity. Order valid inpatient claim intervals
by admission, discharge, and claim stay ID. Merge an interval when its admission
is on or before the running maximum discharge of ALL preceding intervals in its
current chain. This merges overlaps, nested intervals, and same-day transfers.
Use the minimum admission and maximum discharge, retain every contributing claim
ID, count, and paid amount. A conflicting canonical header still participates in
the dated chain, but taints the whole episode and excludes it from the denominator.
Invalid or missing intervals remain as individual auditable excluded episodes;
never discard their claims or money. They cannot establish temporal ordering.

## Index population, numerator and ordered exclusions

An index is a merged episode discharged in 2009 or 2010. Compute the next valid
episode admission across ALL dated episodes before applying denominator exclusions.
An excluded next episode still counts as an observed admission; a header conflict
on that next episode instead makes the candidate index uncertain and excludes it.
A member with ANY undated/invalid inpatient episode is conservatively excluded
from all index denominators because its next admission cannot be established.
Chained readmissions can themselves be index episodes.

Ordered, mutually exclusive first exclusion (retain independent flags too):

1. Invalid or missing episode dates.
2. A member has an invalid or missing dated claim episode.
3. Current or next dated episode has a conflicting canonical header.
4. Discharge is outside performance years 2009 and 2010.
5. Earliest known member death is on or before discharge.
6. Discharge + 30 days is after available-data end 2010-12-31. December 1 has a
   complete window; December 2 does not.
7. Death occurs within the following 30 days (exclude full window rather than
   assume observation after death; this is a conservative project policy).
8. Index-year annual FFS screen is not true.
9. Full-year FFS proxy is not true for every calendar year touched by the 30-day
   follow-up, including the discharge year and next year when crossed.

Annual Part A/B counts of 12 and HMO count of zero form the strict follow-up
proxy. Missing enrollment is ineligible. These counts do NOT verify continuous
or overlapping monthly enrollment. No death-adjusted partial year is claimed to
supply a complete follow-up window. This deliberately conservative denominator
may exclude truly eligible people. The index-year screen uses the existing
is_ffs_eligible proxy and the subsequent full-year proxy is stricter.

For each eligible index, numerator is a next dated admission 1 through 30 days
inclusive after discharge. 31 days is false. A same-day admission has already
merged. Overall rate is numerator / denominator, NULL for zero denominator.

## Provider reporting

Attach by sample/member/discharge year to each retrospective attribution method
(A_visits and B_allowed). Keep unattributed indices visible in coverage totals.
Provider numerator and denominator count index episodes, not unique members.
Publish provider rows only with at least 20 attributed member-years in that
method/year panel; preserve raw rates and the reporting flag for auditing. Panel
size counts the full attributed eligible population, not just hospitalized people.

## Limits

No discharge-status code; inferred transfers can join unrelated same-day claims.
No planned-readmission exclusion, no clinical adjudication, no risk adjustment in
this base measure, no claim of complete enrollment verification. Conflicting and
undated claims make temporal inference uncertain; exclusions expose that cost.
2008 stays contribute temporal history but cannot be performance-year indices.
