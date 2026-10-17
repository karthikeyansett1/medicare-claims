{{ gold_config([{'columns':['merged_stay_id'],'unique':true}, {'columns':['member_key']}]) }}
{{ config(tags=['step9']) }}
with source as (
    select
        *,
        admit_dt is not null and discharge_dt is not null
        and discharge_dt >= admit_dt as valid_dates
    from {{ ref('fct_inpatient_stays') }}
),

ordered as (
    select
        *,
        max(discharge_dt) over (
            partition by member_key order by admit_dt, discharge_dt, stay_id
            rows between unbounded preceding and 1 preceding
        ) as previous_max_discharge
    from source
    where valid_dates
),

islands as (
    select
        *,
        sum(case when admit_dt <= previous_max_discharge then 0 else 1 end)
            over (partition by member_key order by admit_dt, discharge_dt, stay_id) as island
    from ordered
),

merged as (
    select
        min(stay_id) as merged_stay_id,
        member_key,
        _sample_id,
        member_id,
        min(admit_dt) as admit_dt,
        max(discharge_dt) as discharge_dt,
        array_agg(stay_id order by stay_id) as source_stay_ids,
        count(*)::integer as source_claim_count,
        sum(paid_amt) as paid_amt,
        bool_or(has_header_conflict) as has_header_conflict,
        true as valid_dates
    from islands
    group by member_key, _sample_id, member_id, island
)

select * from merged
union all
select
    stay_id as merged_stay_id,
    member_key,
    _sample_id,
    member_id,
    admit_dt,
    discharge_dt,
    array[stay_id] as source_stay_ids,
    1 as source_claim_count,
    paid_amt,
    has_header_conflict,
    valid_dates
from source
where not valid_dates
