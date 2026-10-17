# Profiling definitions and implications

The measured results are in [the raw data profile](data_profile.md); all counters,
column names, source hashes, and missing-value rates are in `data_profile.json`.
This page explains how to interpret them and what they imply for later models.
The source CSVs are unchanged.

## Sources checked

The local [CMS codebook](../data/reference/documentation/CMS_DE_SynPUF_Codebook.pdf)
was checked against every source header. Its inpatient and outpatient segment
entries are IP-3 and OP-3, PDF pages 49 and 77. Both describe segmented claims.
The guide's assumption of one outpatient row per claim therefore needs correction.
The observed columns are preserved in the JSON rather than relying on recalled
column names from the build guide.

Expected Sample 1 row counts come from Table 2 of the local
[CMS Data Users Guide](../data/reference/documentation/CMS_DE_SynPUF_Data_Users_Guide.pdf),
PDF page 8 (printed page 5). That table was visually checked. Counts include
facility segments, not necessarily unique claims or inpatient stays.

The codebook's CAR-52–64 entry labels `LINE_NCH_PMT_AMT` as payment but includes
an inconsistent BETOS description. The [ResDAC payment explanation](https://resdac.org/articles/difference-between-line-payment-amounts-carrier-file)
clarifies that line NCH payment is the Medicare reimbursement amount for a line.
This discrepancy is documented rather than copied into the project's definitions.

The codebook's PDE-8 entry, PDF page 121, calls `TOT_RX_CST_AMT` gross drug cost.
[CMS's explanation of Part D gross drug cost](https://www.cms.gov/newsroom/fact-sheets/medicare-part-d-direct-indirect-remuneration-dir)
also distinguishes total spending across payers from Medicare-only spending.

## Population and null definitions

Every CSV row is included. Identifiers and codes are read as text to preserve
leading zeroes. Empty or whitespace-only strings count as missing; pandas' default
conversion of strings such as `NA` to missing values is disabled. No rows are
excluded for bad dates, negative values, HMO enrollment, or missing NPIs.

Null-rate denominators are rows in the individual file. Date validity requires
an eight-digit value and a valid calendar date; a shape check alone is insufficient.
Invalid nonblank dates are counted separately from blank dates. Date ranges use
only valid values. Synthetic IDs are not real patient or provider identities.

## Grain and future keys

| Source | Profiling grain | Future key considerations |
| --- | --- | --- |
| Beneficiary | Member in a particular annual file | Preserve sample and file year; do not deduplicate a member across years. |
| Inpatient | Claim segment | Preserve sample, member, claim, and segment before deriving stays. |
| Outpatient | Claim segment | Apply the same segment checks as inpatient; CLM_ID alone may repeat. |
| Carrier A and B | Claim with 13 wide slots | Verify uniqueness across both parts; later add line number to a sample-aware claim key. |
| PDE | Prescription drug event | Preserve sample and PDE_ID; gross cost remains distinct from Medicare paid. |

The inpatient (member, admission date, facility) combination is evaluated as a
candidate stay key. It must not silently merge different claim IDs solely because
they share those values. Final stay construction belongs in Step 4 after inspecting
the measured collisions and claim segments.

## Carrier lines and financial completeness

Two denominators are reported: all 13 possible slots per carrier row, and slots
with evidence of activity (HCPCS, rendering NPI, diagnosis, nonzero Medicare paid,
or nonzero allowed). A zero or a blank amount by itself does not make a slot active.
This is an explicit diagnostic definition, not a count of clinical encounters.

The guide's suggested `HCPCS IS NOT NULL` filter is tested by separately summing
payments where HCPCS is absent. Nonzero amounts in those slots must remain
reconcilable even when an office-visit flag cannot be assigned. Rendering NPIs
are counted as missing only within the stated line denominator. Counting empty
unused slots as unattributable clinical services would inflate missingness.

Facility segment payment totals are raw row sums. For repeated member/claim
groups, the report distinguishes equal amounts, differing amounts, missing amounts,
and disagreements in admission, discharge, facility, or principal diagnosis.
The repeated-equal-payment excess is only a diagnostic: equal values alone do not
prove a payment should be removed. Preserve bronze and write an explicit, tested
claim-level policy in silver.

All reported sums use integer cents. Malformed amounts have separate counters.
Negative amounts remain in totals; they are not automatically errors, because
CMS's claim payment documentation describes circumstances that produce negatives.
Do not use a universal nonnegative-payment assertion later without a reason.

## Cost definitions for later measures

Use inpatient/outpatient Medicare claim payment and carrier Medicare line payment
for **medical Medicare paid** after resolving segment policy. Retain carrier
allowed charges as a separate amount. Retain prescription gross drug cost and
patient pay separately. Do not describe medical paid plus gross drug cost as
“total Medicare paid”; that would mix different financial concepts. If a combined
measure is wanted later, name and document its components explicitly.

## Diagnosis grouping

Claim-position, admitting, and carrier line diagnoses are profiled separately to
avoid suggesting their sum is a count of unique diseases or patients. Trim,
uppercase, and remove decimal points only for this diagnostic match against the
2015 CCS source; the raw codes remain unchanged. Blank diagnosis values are
excluded from the coverage denominator. Unmatched nonblank codes and frequencies
are retained in the JSON for Step 8's mapping policy. An unmatched code is not
necessarily invalid; mapping scope and historical coding also matter.

## Enrollment and temporal anomalies

The A=12, B=12, HMO=0 count is a strict annual screening population, not the final
cost denominator. Do not infer that annual Part A and Part B totals describe the
same covered months. Death exceptions and observation-window rules still need
to be specified before calculating member months and quality rates.

The earliest valid nonblank death date across annual files is used to flag
service-start-after-death records. Conflicting death dates are reported. Claim end
after death is separate because billing windows may extend beyond the service
start. These are flags for review, not automatic exclusions or evidence of fraud.

## Measured findings and modeling decisions

The full scan covers **11,494,963 rows**, including 343,644 beneficiary-year rows
and 11,151,319 claim-segment, professional-claim, and drug-event rows. All eight
file counts match CMS Table 2. Calling all these rows unique claims would be wrong.

Carrier files contain **9,388,987 active slots** by the stated definition.
There are **372,680 nonzero-paid slots without HCPCS**, carrying **$20,695,070**.
A nonblank-HCPCS-only unpivot would lose those payments. Keep payment-bearing
slots in the financial fact and assign office-visit status only when the code
supports it. **20,289 active slots lack rendering NPI**; preserve their amounts
while flagging them as unattributable to a rendering provider.

There are **68 inpatient** and **10,975 outpatient** member/claim groups with
multiple segments. No (member, claim, segment) key duplicates were found. Payments
differ in 58 and 10,357 of those groups respectively. Among the inpatient groups,
61 disagree on admission date and 48 disagree on facility; outpatient facility
values differ in 7,655 groups. Principal diagnoses differ in every multi-segment
group. These synthetic inconsistencies make blind header aggregation unsafe.

Use **(sample, member, claim)** as the initial claim/episode identity and retain
segment lineage. Do not automatically merge distinct claim IDs just because
member, admission date, and facility agree: 57 candidate combinations contain
multiple claim IDs. The initial episode identity is an analytical convention,
not proof of a clinical stay. In Step 4, define canonical headers and conflict
flags explicitly; Step 9 must state how conflicting episodes affect readmission
eligibility. Preserve row-level payment sums as the raw reconciliation baseline.
Do not deduplicate amounts solely because two segments have equal payments.

There are **55 inpatient and 2,566 outpatient negative payment values**. Retain
and flag them rather than replacing them with zero. All profiled nonblank dates
are valid calendar dates, and no service starts after the recorded death date
were found. There are 226 inpatient and 312 outpatient rows with service starts
before 2008; their presence is consistent with claims crossing the year boundary,
so keep them until a measure's time-window rule is applied.

Outpatient claim diagnoses contain 5,675 unmatched occurrences, all `OTHER`.
Carrier diagnosis scopes also include unmatched tokens such as `XX000`. Keep an
explicit unknown category later; do not discard those claims or invent a CCS
mapping. Detailed unmatched-code frequencies remain in the JSON.

The focused facility follow-up reproduced every earlier inpatient/outpatient
counter while adding field-by-field header-conflict counts. It did not rerun or
change the carrier or PDE analysis.
