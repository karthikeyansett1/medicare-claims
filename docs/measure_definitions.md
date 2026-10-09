# Financial and grain definitions

Status: Step 5 foundational definitions. Attribution, clinical grouping,
readmissions, adjusted performance measures, and the assistant are later steps.
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
observation. Provider metrics and readmission denominators are not defined yet.
`dim_dx_ccs` is intentionally deferred to the mapping and coverage checks in Step 8.
