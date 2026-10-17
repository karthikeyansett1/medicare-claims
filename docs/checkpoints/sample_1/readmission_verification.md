# Readmission verification

Independent Python reconstruction checked 839,280 fields across 64,560 episodes and 161,870 provider rows. Every one of 66,705 source claims occurs exactly once.

Overall: 1,579 / 25,062 = 6.3004%.

| First exclusion | Removed | Remaining |
| --- | ---: | ---: |
| All merged/audit episodes | 0 | 64,560 |
| 03_header_conflict | 93 | 64,467 |
| 04_outside_performance_year | 26,029 | 38,438 |
| 05_death_on_or_before_discharge | 3 | 38,435 |
| 06_incomplete_data_window | 309 | 38,126 |
| 07_death_in_followup | 56 | 38,070 |
| 08_index_ffs_proxy | 12,828 | 25,242 |
| 09_followup_ffs_proxy | 180 | 25,062 |

Invalid/conflicting claims remain in source and financial reconciliation. Rates are synthetic, unadjusted, and use an annual enrollment proxy. See the canonical specification.

| Attribution | Assigned | Eligible indices | Readmissions |
| --- | --- | ---: | ---: |
| A_visits | False | 1,322 | 50 |
| A_visits | True | 23,740 | 1,529 |
| B_allowed | False | 494 | 20 |
| B_allowed | True | 24,568 | 1,559 |
