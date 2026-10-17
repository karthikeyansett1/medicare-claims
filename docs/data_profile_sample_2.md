# Sample 2 raw data profile

All eight source files were profiled in full without altering rows. This is a
source inventory and methodology diagnostic, not a cleaned warehouse or a
provider-performance result. Detailed counters and column null rates are in
`data_profile_sample_2.json`. Interpretation and source references are in
[profiling decisions](profile_interpretation.md).

## Source counts and keys

| File type | Rows | CMS expected | Distinct members | Distinct event IDs | Duplicate ID excess rows |
| --- | ---: | ---: | ---: | ---: | ---: |
| beneficiary_2008 | 116,395 | 116,395 | 116,395 | 116,395 | 0 |
| beneficiary_2009 | 114,618 | 114,618 | 114,618 | 114,618 | 0 |
| beneficiary_2010 | 112,845 | 112,845 | 112,845 | 112,845 | 0 |
| carrier_a | 2,372,957 | 2,372,957 | 49,153 | 2,372,957 | 0 |
| carrier_b | 2,372,957 | 2,372,957 | 49,534 | 2,372,957 | 0 |
| inpatient | 66,494 | 66,494 | 37,661 | 66,434 | 60 |
| outpatient | 792,562 | 792,562 | 85,295 | 781,553 | 11,009 |
| pde | 5,561,154 | 5,561,154 | 99,746 | 5,561,154 | 0 |

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
| beneficiary_2008 | BENE_BIRTH_DT | 116,395 | 0 | 1909-01-01 | 1983-12-01 |
| beneficiary_2008 | BENE_DEATH_DT | 1,777 | 0 | 2008-01-01 | 2008-12-01 |
| beneficiary_2009 | BENE_BIRTH_DT | 114,618 | 0 | 1909-01-01 | 1983-12-01 |
| beneficiary_2009 | BENE_DEATH_DT | 1,773 | 0 | 2009-01-01 | 2009-12-01 |
| beneficiary_2010 | BENE_BIRTH_DT | 112,845 | 0 | 1909-01-01 | 1983-12-01 |
| beneficiary_2010 | BENE_DEATH_DT | 1,818 | 0 | 2010-01-01 | 2010-12-01 |
| carrier_a | CLM_FROM_DT | 2,372,957 | 0 | 2008-01-01 | 2010-12-31 |
| carrier_a | CLM_THRU_DT | 2,372,957 | 0 | 2008-01-01 | 2010-12-31 |
| carrier_b | CLM_FROM_DT | 2,372,957 | 0 | 2008-01-01 | 2010-12-31 |
| carrier_b | CLM_THRU_DT | 2,372,957 | 0 | 2008-01-01 | 2010-12-31 |
| inpatient | CLM_ADMSN_DT | 66,494 | 0 | 2007-11-27 | 2010-12-29 |
| inpatient | CLM_FROM_DT | 66,434 | 0 | 2007-11-27 | 2010-12-29 |
| inpatient | CLM_THRU_DT | 66,434 | 0 | 2008-01-01 | 2010-12-31 |
| inpatient | NCH_BENE_DSCHRG_DT | 66,494 | 0 | 2008-01-01 | 2010-12-31 |
| outpatient | CLM_FROM_DT | 781,361 | 0 | 2007-12-12 | 2010-12-31 |
| outpatient | CLM_THRU_DT | 781,361 | 0 | 2008-01-01 | 2010-12-31 |
| pde | SRVC_DT | 5,561,154 | 0 | 2008-01-01 | 2010-12-31 |

## 2 Carrier line structure and reconciliation

An active slot has HCPCS, NPI, line diagnosis, nonzero paid, or nonzero allowed amount.
This is a profiling definition, not the final model inclusion rule.

| Check | Carrier A | Carrier B |
| --- | ---: | ---: |
| possible_line_slots | 30,848,441 | 30,848,441 |
| active_line_slots | 4,698,620 | 4,700,330 |
| hcpcs_present_lines | 4,425,332 | 4,429,019 |
| active_missing_hcpcs | 273,288 | 271,311 |
| nonzero_paid_missing_hcpcs | 187,386 | 185,805 |
| paid_cents_missing_hcpcs | 1,036,596,000 | 1,027,399,000 |
| paid_cents_hcpcs_present | 19,719,490,000 | 19,726,263,000 |

Cents counters are integer cents. Payments on missing-HCPCS slots must not
silently disappear during the later unpivot.

## 3 Facility claim segments

| Check | Inpatient | Outpatient |
| --- | ---: | ---: |
| claim_groups | 66,434 | 781,553 |
| multirow_claim_groups | 60 | 11,009 |
| duplicate_segment_key_excess_rows | 0 | 0 |
| repeated_equal_payment_groups | 9 | 599 |
| differing_payment_groups | 51 | 10,410 |
| missing_payment_groups | 0 | 0 |
| repeated_equal_nonzero_payment_groups | 9 | 592 |
| repeat_payment_excess_cents | 34,000,000 | 71,037,000 |
| differing_header_groups | 60 | 11,009 |
| differing_admission_groups | 51 | N/A |
| differing_discharge_groups | 0 | N/A |
| differing_provider_groups | 41 | 7,919 |
| differing_principal_diagnosis_groups | 60 | 11,009 |

Equal payments across segments are a duplication diagnostic, not proof that
every repeated amount should be deleted. Differing-payment groups require explicit policy.
Inpatient candidate (member, admission, facility) groups: 66,438; keys containing multiple claim IDs: 54.

## 4 Diagnosis format and CCS coverage

Counts are diagnosis-position occurrences, not people. Claim, admitting, and line
diagnoses are separate scopes. Match uses trimmed uppercase codes without decimals.

| File | Scope | Nonblank | With decimal | Unmatched occurrences | Distinct unmatched codes |
| --- | --- | ---: | ---: | ---: | ---: |
| carrier_a | claim | 5,066,084 | 0 | 567 | 40 |
| carrier_a | line | 4,562,465 | 0 | 1,147 | 40 |
| carrier_b | claim | 5,065,736 | 0 | 524 | 51 |
| carrier_b | line | 4,565,128 | 0 | 1,000 | 45 |
| inpatient | admitting | 65,897 | 0 | 0 | 0 |
| inpatient | claim | 535,659 | 0 | 0 | 0 |
| outpatient | admitting | 194,733 | 0 | 6 | 6 |
| outpatient | claim | 2,078,064 | 0 | 5,640 | 1 |

The JSON includes each unmatched code and its occurrence count. No codes were dropped.

## 5 Missing rendering NPIs

| Scope | Carrier A | Carrier B |
| --- | ---: | ---: |
| active_missing_npi | 9,963 | 9,957 |
| hcpcs_present_missing_npi | 9,421 | 9,394 |

Blank rendering NPIs prevent provider attribution for those slots; zero-paid
empty slots are not counted as active solely because the payment field is populated.

## 6 Synthetic temporal and linkage anomalies

Death date is the earliest valid nonblank value across all three beneficiary files.
Members with conflicting nonblank death dates: 0.
Start means admission for inpatient, claim-from for outpatient/carrier, and service
date for PDE. End-after-death can reflect billing timing and is reported separately.

| File | Orphan member rows | Known-death rows | Start after death | End after death | End before start | Discharge before admission |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| carrier_a | 0 | 58,268 | 0 | 0 | 0 | 0 |
| carrier_b | 0 | 61,185 | 0 | 0 | 0 | 0 |
| inpatient | 0 | 1,723 | 0 | 0 | 0 | 0 |
| outpatient | 0 | 19,962 | 0 | 0 | 0 | 0 |
| pde | 0 | 135,970 | 0 | 0 | 0 | 0 |

Facility start dates can precede 2008 while the claim ends during the study
period. These rows remain in the source baseline; they are not automatically invalid.
Start dates outside 2008–2010: inpatient 207; outpatient 330.
Discharge-before-admission applies only to inpatient; other file types have no
admission/discharge pair and their zero counter means the check is not applicable.

## 7 Financial amounts

Raw facility sums include all segments and are not yet deduplicated. Carrier sums
include all 13 slots. PDE gross drug cost and patient pay remain separate from
Medicare medical payments. Null or malformed amounts do not become zero silently;
the table totals valid amounts and reports invalid counts.

| File | Amount | Total dollars | Negative values | Invalid nonblank | Blank |
| --- | --- | ---: | ---: | ---: | ---: |
| carrier_a | LINE_ALOWD_CHRG_AMT | 267,513,490.00 | 0 | 0 | 0 |
| carrier_a | LINE_NCH_PMT_AMT | 207,560,860.00 | 0 | 0 | 0 |
| carrier_b | LINE_ALOWD_CHRG_AMT | 287,436,660.00 | 0 | 0 | 0 |
| carrier_b | LINE_NCH_PMT_AMT | 207,536,620.00 | 0 | 0 | 0 |
| inpatient | CLM_PMT_AMT | 634,063,230.00 | 58 | 0 | 0 |
| outpatient | CLM_PMT_AMT | 225,486,960.00 | 2,557 | 0 | 0 |
| pde | PTNT_PAY_AMT | 57,359,650.00 | 0 | 0 | 0 |
| pde | TOT_RX_CST_AMT | 340,970,780.00 | 0 | 0 | 0 |

## 8 Enrollment and chronic flags

The screening count below uses exactly A=12, B=12, HMO=0. It is not the final
eligible population: enrollment through death and measure-specific windows are undecided.

| Year | Member rows | HMO months above zero | A12 B12 HMO0 | Invalid month cells | Invalid chronic flag cells |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2008 | 116,395 | 26,872 | 73,274 | 0 | 0 |
| 2009 | 114,618 | 33,419 | 72,650 | 0 | 0 |
| 2010 | 112,845 | 36,606 | 63,359 | 0 | 0 |

## Key-column missingness

Empty strings after trimming are missing. Literal NA and other codes remain values.
The JSON records every column; this table focuses on linking and interpretation keys.

| File | Column | Missing rows | Missing percent |
| --- | --- | ---: | ---: |
| beneficiary_2008 | DESYNPUF_ID | 0 | 0.0000% |
| beneficiary_2008 | BENE_DEATH_DT | 114,618 | 98.4733% |
| beneficiary_2009 | DESYNPUF_ID | 0 | 0.0000% |
| beneficiary_2009 | BENE_DEATH_DT | 112,845 | 98.4531% |
| beneficiary_2010 | DESYNPUF_ID | 0 | 0.0000% |
| beneficiary_2010 | BENE_DEATH_DT | 111,027 | 98.3889% |
| carrier_a | DESYNPUF_ID | 0 | 0.0000% |
| carrier_a | CLM_ID | 0 | 0.0000% |
| carrier_b | DESYNPUF_ID | 0 | 0.0000% |
| carrier_b | CLM_ID | 0 | 0.0000% |
| inpatient | DESYNPUF_ID | 0 | 0.0000% |
| inpatient | CLM_ID | 0 | 0.0000% |
| inpatient | SEGMENT | 0 | 0.0000% |
| inpatient | PRVDR_NUM | 0 | 0.0000% |
| inpatient | AT_PHYSN_NPI | 672 | 1.0106% |
| inpatient | CLM_ADMSN_DT | 0 | 0.0000% |
| inpatient | NCH_BENE_DSCHRG_DT | 0 | 0.0000% |
| outpatient | DESYNPUF_ID | 0 | 0.0000% |
| outpatient | CLM_ID | 0 | 0.0000% |
| outpatient | SEGMENT | 0 | 0.0000% |
| outpatient | PRVDR_NUM | 0 | 0.0000% |
| outpatient | AT_PHYSN_NPI | 17,811 | 2.2473% |
| pde | DESYNPUF_ID | 0 | 0.0000% |
| pde | PDE_ID | 0 | 0.0000% |
| pde | PROD_SRVC_ID | 0 | 0.0000% |

## Reproduce and validate

Run `make profile` after `make download`.
Input hashes are checked against the acquisition manifest. Expected row counts
come from CMS Data Users Guide Table 2, PDF page 8 (printed page 5).
SQLite temporary storage is discarded when the run completes. No database load
or source-data filtering occurs. Step 3 must reconcile bronze against these exact counts.

## Bronze reconciliation

Step 3 database counts and financial checks are recorded separately in
[bronze reconciliation](bronze_reconciliation.md), preserving this source baseline.
