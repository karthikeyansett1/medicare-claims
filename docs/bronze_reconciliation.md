# Bronze load reconciliation

The five bronze tables retain every source column as text, plus sample, file,
file-year, and load-time lineage. Source blanks remain empty strings.
No eligibility filtering, claim collapsing, or type conversion was applied.

| Table | Source rows | PostgreSQL rows | Difference | Raw columns |
| --- | ---: | ---: | ---: | ---: |
| bronze.beneficiary | 687,502 | 687,502 | 0 | 32 |
| bronze.inpatient | 133,267 | 133,267 | 0 | 81 |
| bronze.outpatient | 1,583,352 | 1,583,352 | 0 | 76 |
| bronze.carrier | 9,487,249 | 9,487,249 | 0 | 142 |
| bronze.pde | 11,113,575 | 11,113,575 | 0 | 8 |

## File-level checks

| Source file | Sample | File year | Source rows | PostgreSQL rows | Difference |
| --- | ---: | --- | ---: | ---: | ---: |
| DE1_0_2008_Beneficiary_Summary_File_Sample_1.csv | 1 | 2008 | 116,352 | 116,352 | 0 |
| DE1_0_2008_Beneficiary_Summary_File_Sample_2.csv | 2 | 2008 | 116,395 | 116,395 | 0 |
| DE1_0_2009_Beneficiary_Summary_File_Sample_1.csv | 1 | 2009 | 114,538 | 114,538 | 0 |
| DE1_0_2009_Beneficiary_Summary_File_Sample_2.csv | 2 | 2009 | 114,618 | 114,618 | 0 |
| DE1_0_2010_Beneficiary_Summary_File_Sample_1.csv | 1 | 2010 | 112,754 | 112,754 | 0 |
| DE1_0_2010_Beneficiary_Summary_File_Sample_2.csv | 2 | 2010 | 112,845 | 112,845 | 0 |
| DE1_0_2008_to_2010_Inpatient_Claims_Sample_1.csv | 1 | N/A | 66,773 | 66,773 | 0 |
| DE1_0_2008_to_2010_Inpatient_Claims_Sample_2.csv | 2 | N/A | 66,494 | 66,494 | 0 |
| DE1_0_2008_to_2010_Outpatient_Claims_Sample_1.csv | 1 | N/A | 790,790 | 790,790 | 0 |
| DE1_0_2008_to_2010_Outpatient_Claims_Sample_2.csv | 2 | N/A | 792,562 | 792,562 | 0 |
| DE1_0_2008_to_2010_Carrier_Claims_Sample_1A.csv | 1 | N/A | 2,370,667 | 2,370,667 | 0 |
| DE1_0_2008_to_2010_Carrier_Claims_Sample_1B.csv | 1 | N/A | 2,370,668 | 2,370,668 | 0 |
| DE1_0_2008_to_2010_Carrier_Claims_Sample_2A.csv | 2 | N/A | 2,372,957 | 2,372,957 | 0 |
| DE1_0_2008_to_2010_Carrier_Claims_Sample_2B.csv | 2 | N/A | 2,372,957 | 2,372,957 | 0 |
| DE1_0_2008_to_2010_Prescription_Drug_Events_Sample_1.csv | 1 | N/A | 5,552,421 | 5,552,421 | 0 |
| DE1_0_2008_to_2010_Prescription_Drug_Events_Sample_2.csv | 2 | N/A | 5,561,154 | 5,561,154 | 0 |

Total rows loaded: **23,004,945**.

All per-file financial sums checked against Step 2 agree. Carrier checks cover
all 13 payment and all 13 allowed columns, without excluding blank-HCPCS slots.
The JSON records each exact sum in integer cents and the corresponding source hash.
These are raw reconciliation totals, not finalized cost measures.

The transaction commits only after COPY counts, grouped database counts, lineage,
column types, UNLOGGED status, and financial totals pass. Each file also has its
SHA-256 recalculated during transmission.

Run `make verify-bronze` to recheck the current database without reloading it.
UNLOGGED tables can be truncated after a crash; rerun `make bronze` to rebuild.
Source files and their manifest remain the recovery source.
