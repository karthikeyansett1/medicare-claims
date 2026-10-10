# Financial and grain definitions

Status: financial and attribution definitions, with the canonical Step 9
readmission specification linked below. Adjusted performance and assistant are later steps.
Source: historical synthetic CMS DE-SynPUF Sample 1, not identifiable patients
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

The canonical readmission specification is
[assistant/measure_definitions.md](../assistant/measure_definitions.md), written
before its SQL implementation. It defines episode merging, ordered exclusions,
annual follow-up enrollment proxies, and provider denominator/reporting rules.
