# Sample 1 raw data profile

All eight source files were profiled in full without altering rows. This is a
source inventory and methodology diagnostic, not a cleaned warehouse or a
provider-performance result. Detailed counters and column null rates are in
`data_profile.json`. Interpretation and source references are in
[profiling decisions](profile_interpretation.md).

## Source counts and keys

| File type | Rows | CMS expected | Distinct members | Distinct event IDs | Duplicate ID excess rows |
| --- | ---: | ---: | ---: | ---: | ---: |
| beneficiary_2008 | 116,352 | 116,352 | 116,352 | 116,352 | 0 |
| beneficiary_2009 | 114,538 | 114,538 | 114,538 | 114,538 | 0 |
| beneficiary_2010 | 112,754 | 112,754 | 112,754 | 112,754 | 0 |
| carrier_a | 2,370,667 | 2,370,667 | 49,278 | 2,370,667 | 0 |
| carrier_b | 2,370,668 | 2,370,668 | 49,349 | 2,370,668 | 0 |
| inpatient | 66,773 | 66,773 | 37,780 | 66,705 | 68 |
| outpatient | 790,790 | 790,790 | 85,272 | 779,815 | 10,975 |
| pde | 5,552,421 | 5,552,421 | 99,538 | 5,552,421 | 0 |

Event IDs are DESYNPUF_ID for beneficiary files, PDE_ID for drug events,
and CLM_ID for claims. Repeated facility claim IDs can be segments, not duplicate claims.
Carrier A/B overlapping claim IDs: **0**.

## File grain and verified headers

| File type | Observed source grain | Columns |
| --- | --- | ---: |
| beneficiary_2008 | Beneficiary in one file year | 32 |
| beneficiary_2009 | Beneficiary in one file year | 32 |
| beneficiary_2010 | Beneficiary in one file year | 32 |
| carrier_a | Professional claim with 13 wide line slots | 142 |
| carrier_b | Professional claim with 13 wide line slots | 142 |
| inpatient | Claim segment; CLM_ID can repeat | 81 |
| outpatient | Claim segment; CLM_ID can repeat | 76 |
| pde | Prescription drug event | 8 |

## 1 Date fields

Dates require exactly eight digits and a valid calendar date.
Blank values are counted separately; ranges exclude blanks and invalid dates.

| File | Field | Nonblank | Invalid nonblank | Minimum | Maximum |
| --- | --- | ---: | ---: | --- | --- |
| beneficiary_2008 | BENE_BIRTH_DT | 116,352 | 0 | 1909-01-01 | 1983-12-01 |
| beneficiary_2008 | BENE_DEATH_DT | 1,814 | 0 | 2008-01-01 | 2008-12-01 |
| beneficiary_2009 | BENE_BIRTH_DT | 114,538 | 0 | 1909-01-01 | 1983-12-01 |
| beneficiary_2009 | BENE_DEATH_DT | 1,784 | 0 | 2009-01-01 | 2009-12-01 |
| beneficiary_2010 | BENE_BIRTH_DT | 112,754 | 0 | 1909-01-01 | 1983-12-01 |
| beneficiary_2010 | BENE_DEATH_DT | 1,863 | 0 | 2010-01-01 | 2010-12-01 |
| carrier_a | CLM_FROM_DT | 2,370,667 | 0 | 2008-01-01 | 2010-12-31 |
| carrier_a | CLM_THRU_DT | 2,370,667 | 0 | 2008-01-01 | 2010-12-31 |
| carrier_b | CLM_FROM_DT | 2,370,668 | 0 | 2008-01-01 | 2010-12-31 |
| carrier_b | CLM_THRU_DT | 2,370,668 | 0 | 2008-01-01 | 2010-12-31 |
| inpatient | CLM_ADMSN_DT | 66,773 | 0 | 2007-11-27 | 2010-12-30 |
| inpatient | CLM_FROM_DT | 66,705 | 0 | 2007-11-27 | 2010-12-30 |
| inpatient | CLM_THRU_DT | 66,705 | 0 | 2008-01-01 | 2010-12-31 |
| inpatient | NCH_BENE_DSCHRG_DT | 66,773 | 0 | 2008-01-01 | 2010-12-31 |
| outpatient | CLM_FROM_DT | 779,537 | 0 | 2007-12-12 | 2010-12-31 |
| outpatient | CLM_THRU_DT | 779,537 | 0 | 2008-01-01 | 2010-12-31 |
| pde | SRVC_DT | 5,552,421 | 0 | 2008-01-01 | 2010-12-31 |

## 2 Carrier line structure and reconciliation

An active slot has HCPCS, NPI, line diagnosis, nonzero paid, or nonzero allowed amount.
This is a profiling definition, not the final model inclusion rule.

| Check | Carrier A | Carrier B |
| --- | ---: | ---: |
| possible_line_slots | 30,818,671 | 30,818,684 |
| active_line_slots | 4,694,496 | 4,694,491 |
| hcpcs_present_lines | 4,423,377 | 4,422,549 |
| active_missing_hcpcs | 271,119 | 271,942 |
| nonzero_paid_missing_hcpcs | 186,260 | 186,420 |
| paid_cents_missing_hcpcs | 1,032,434,000 | 1,037,073,000 |
| paid_cents_hcpcs_present | 19,696,772,000 | 19,694,090,000 |

Cents counters are integer cents. Payments on missing-HCPCS slots must not
silently disappear during the later unpivot.

## 3 Facility claim segments

| Check | Inpatient | Outpatient |
| --- | ---: | ---: |
| claim_groups | 66,705 | 779,815 |
| multirow_claim_groups | 68 | 10,975 |
| duplicate_segment_key_excess_rows | 0 | 0 |
| repeated_equal_payment_groups | 10 | 618 |
| differing_payment_groups | 58 | 10,357 |
| missing_payment_groups | 0 | 0 |
| repeated_equal_nonzero_payment_groups | 9 | 607 |
| repeat_payment_excess_cents | 12,100,000 | 77,762,000 |
| differing_header_groups | 68 | 10,975 |
| differing_admission_groups | 61 | N/A |
| differing_discharge_groups | 0 | N/A |
| differing_provider_groups | 48 | 7,655 |
| differing_principal_diagnosis_groups | 68 | 10,975 |

Equal payments across segments are a duplication diagnostic, not proof that
every repeated amount should be deleted. Differing-payment groups require explicit policy.
Inpatient candidate (member, admission, facility) groups: 66,715; keys containing multiple claim IDs: 57.

## 4 Diagnosis format and CCS coverage

Counts are diagnosis-position occurrences, not people. Claim, admitting, and line
diagnoses are separate scopes. Match uses trimmed uppercase codes without decimals.

| File | Scope | Nonblank | With decimal | Unmatched occurrences | Distinct unmatched codes |
| --- | --- | ---: | ---: | ---: | ---: |
| carrier_a | claim | 5,060,751 | 0 | 556 | 51 |
| carrier_a | line | 4,557,894 | 0 | 987 | 33 |
| carrier_b | claim | 5,061,254 | 0 | 504 | 41 |
| carrier_b | line | 4,559,408 | 0 | 1,047 | 27 |
| inpatient | admitting | 66,174 | 0 | 0 | 0 |
| inpatient | claim | 537,271 | 0 | 0 | 0 |
| outpatient | admitting | 194,486 | 0 | 7 | 6 |
| outpatient | claim | 2,073,796 | 0 | 5,675 | 1 |

The JSON includes each unmatched code and its occurrence count. No codes were dropped.

## 5 Missing rendering NPIs

| Scope | Carrier A | Carrier B |
| --- | ---: | ---: |
| active_missing_npi | 10,092 | 10,197 |
| hcpcs_present_missing_npi | 9,567 | 9,632 |

Blank rendering NPIs prevent provider attribution for those slots; zero-paid
empty slots are not counted as active solely because the payment field is populated.

## 6 Synthetic temporal and linkage anomalies

Death date is the earliest valid nonblank value across all three beneficiary files.
Members with conflicting nonblank death dates: 0.
Start means admission for inpatient, claim-from for outpatient/carrier, and service
date for PDE. End-after-death can reflect billing timing and is reported separately.

| File | Orphan member rows | Known-death rows | Start after death | End after death | End before start | Discharge before admission |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| carrier_a | 0 | 60,877 | 0 | 0 | 0 | 0 |
| carrier_b | 0 | 61,634 | 0 | 0 | 0 | 0 |
| inpatient | 0 | 1,853 | 0 | 0 | 0 | 0 |
| outpatient | 0 | 21,242 | 0 | 0 | 0 | 0 |
| pde | 0 | 137,116 | 0 | 0 | 0 | 0 |

Facility start dates can precede 2008 while the claim ends during the study
period. These rows remain in the source baseline; they are not automatically invalid.
Start dates outside 2008–2010: inpatient 226; outpatient 312.
Discharge-before-admission applies only to inpatient; other file types have no
admission/discharge pair and their zero counter means the check is not applicable.

## 7 Financial amounts

Raw facility sums include all segments and are not yet deduplicated. Carrier sums
include all 13 slots. PDE gross drug cost and patient pay remain separate from
Medicare medical payments. Null or malformed amounts do not become zero silently;
the table totals valid amounts and reports invalid counts.

| File | Amount | Total dollars | Negative values | Invalid nonblank | Blank |
| --- | --- | ---: | ---: | ---: | ---: |
| carrier_a | LINE_ALOWD_CHRG_AMT | 267,338,180.00 | 0 | 0 | 0 |
| carrier_a | LINE_NCH_PMT_AMT | 207,292,060.00 | 0 | 0 | 0 |
| carrier_b | LINE_ALOWD_CHRG_AMT | 267,247,710.00 | 0 | 0 | 0 |
| carrier_b | LINE_NCH_PMT_AMT | 207,311,630.00 | 0 | 0 | 0 |
| inpatient | CLM_PMT_AMT | 639,260,180.00 | 55 | 0 | 0 |
| outpatient | CLM_PMT_AMT | 224,524,710.00 | 2,566 | 0 | 0 |
| pde | PTNT_PAY_AMT | 57,238,770.00 | 0 | 0 | 0 |
| pde | TOT_RX_CST_AMT | 340,943,210.00 | 0 | 0 | 0 |

## 8 Enrollment and chronic flags

The screening count below uses exactly A=12, B=12, HMO=0. It is not the final
eligible population: enrollment through death and measure-specific windows are undecided.

| Year | Member rows | HMO months above zero | A12 B12 HMO0 | Invalid month cells | Invalid chronic flag cells |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2008 | 116,352 | 26,890 | 73,210 | 0 | 0 |
| 2009 | 114,538 | 33,330 | 72,685 | 0 | 0 |
| 2010 | 112,754 | 36,531 | 63,293 | 0 | 0 |

## Key-column missingness

Empty strings after trimming are missing. Literal NA and other codes remain values.
The JSON records every column; this table focuses on linking and interpretation keys.

| File | Column | Missing rows | Missing percent |
| --- | --- | ---: | ---: |
| beneficiary_2008 | DESYNPUF_ID | 0 | 0.0000% |
| beneficiary_2008 | BENE_DEATH_DT | 114,538 | 98.4409% |
| beneficiary_2009 | DESYNPUF_ID | 0 | 0.0000% |
| beneficiary_2009 | BENE_DEATH_DT | 112,754 | 98.4424% |
| beneficiary_2010 | DESYNPUF_ID | 0 | 0.0000% |
| beneficiary_2010 | BENE_DEATH_DT | 110,891 | 98.3477% |
| carrier_a | DESYNPUF_ID | 0 | 0.0000% |
| carrier_a | CLM_ID | 0 | 0.0000% |
| carrier_b | DESYNPUF_ID | 0 | 0.0000% |
| carrier_b | CLM_ID | 0 | 0.0000% |
| inpatient | DESYNPUF_ID | 0 | 0.0000% |
| inpatient | CLM_ID | 0 | 0.0000% |
| inpatient | SEGMENT | 0 | 0.0000% |
| inpatient | PRVDR_NUM | 0 | 0.0000% |
| inpatient | AT_PHYSN_NPI | 673 | 1.0079% |
| inpatient | CLM_ADMSN_DT | 0 | 0.0000% |
| inpatient | NCH_BENE_DSCHRG_DT | 0 | 0.0000% |
| outpatient | DESYNPUF_ID | 0 | 0.0000% |
| outpatient | CLM_ID | 0 | 0.0000% |
| outpatient | SEGMENT | 0 | 0.0000% |
| outpatient | PRVDR_NUM | 0 | 0.0000% |
| outpatient | AT_PHYSN_NPI | 17,790 | 2.2496% |
| pde | DESYNPUF_ID | 0 | 0.0000% |
| pde | PDE_ID | 0 | 0.0000% |
| pde | PROD_SRVC_ID | 0 | 0.0000% |

## Reproduce and validate

Run `make profile` after `make download`.
Input hashes are checked against the acquisition manifest. Expected row counts
come from CMS Data Users Guide Table 2, PDF page 8 (printed page 5).
SQLite temporary storage is discarded when the run completes. No database load
or source-data filtering occurs. Step 3 must reconcile bronze against these exact counts.
