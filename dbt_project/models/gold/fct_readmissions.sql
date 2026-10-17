{{ gold_config([{'columns':['merged_stay_id'],'unique':true}, {'columns':['member_key','year']}]) }}
{{ config(tags=['step9']) }}
select
    *,
    next_admit_dt - discharge_dt as days_to_next_admit,
    exclusion_reason is null as is_index_eligible,
    case
        when exclusion_reason is null then coalesce(next_admit_dt - discharge_dt between 1 and 30, false)
        else null
    end as is_readmit_30d
from {{ ref('int_index_stays') }}
