# Readmission verification

Independent Python reconstruction checked 1,674,582 fields across 128,814 episodes and 323,458 provider rows. Every one of 133,139 source claims occurs exactly once.

Overall: 3,233 / 49,998 = 6.4663%.

| First exclusion | Removed | Remaining |
| --- | ---: | ---: |
| All merged/audit episodes | 0 | 128,814 |
| 03_header_conflict | 183 | 128,631 |
| 04_outside_performance_year | 51,868 | 76,763 |
| 05_death_on_or_before_discharge | 3 | 76,760 |
| 06_incomplete_data_window | 585 | 76,175 |
| 07_death_in_followup | 99 | 76,076 |
| 08_index_ffs_proxy | 25,738 | 50,338 |
| 09_followup_ffs_proxy | 340 | 49,998 |

Invalid/conflicting claims remain in source and financial reconciliation. Rates are synthetic, unadjusted, and use an annual enrollment proxy. See the canonical specification.

| Attribution | Assigned | Eligible indices | Readmissions |
| --- | --- | ---: | ---: |
| A_visits | False | 2,702 | 116 |
| A_visits | True | 47,296 | 3,117 |
| B_allowed | False | 1,024 | 51 |
| B_allowed | True | 48,974 | 3,182 |
