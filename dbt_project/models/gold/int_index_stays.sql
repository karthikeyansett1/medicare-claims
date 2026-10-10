{{ gold_config([{'columns':['merged_stay_id'],'unique':true}, {'columns':['member_key','year']}]) }}
{{ config(tags=['step9']) }}
with sequence as (
    select
        merged_stay_id,
        lead(admit_dt) over (partition by member_key order by admit_dt, merged_stay_id) as next_admit_dt,
        lead(has_header_conflict) over (
            partition by member_key order by admit_dt, merged_stay_id
        ) as next_has_header_conflict
    from {{ ref('int_stays_merged') }}
    where valid_dates
),

member_audit as (
    select
        member_key,
        bool_or(not valid_dates) as has_unordered_episode
    from {{ ref('int_stays_merged') }}
    group by member_key
),

flags as (
    select
        s.*,
        extract(year from s.discharge_dt)::integer as year,
        q.next_admit_dt,
        q.next_has_header_conflict,
        d.death_dt,
        not s.valid_dates as exclude_invalid_dates,
        a.has_unordered_episode as exclude_unordered_member,
        s.has_header_conflict or coalesce(q.next_has_header_conflict, false) as exclude_header_conflict,
        coalesce(extract(year from s.discharge_dt) not in (2009, 2010), true) as exclude_performance_year,
        coalesce(d.death_dt <= s.discharge_dt, false) as exclude_death_before_discharge,
        coalesce(s.discharge_dt + 30 > date '2010-12-31', true) as exclude_incomplete_data,
        coalesce(d.death_dt > s.discharge_dt and d.death_dt <= s.discharge_dt + 30, false)
            as exclude_death_in_followup,
        not coalesce(y.is_ffs_eligible, false) as exclude_index_ffs,
        not(coalesce(y.is_full_year_ffs, false) and coalesce(f.is_full_year_ffs, false))
            as exclude_followup_ffs
    from {{ ref('int_stays_merged') }} as s
    left join sequence as q on s.merged_stay_id = q.merged_stay_id
    left join member_audit as a on s.member_key = a.member_key
    left join {{ ref('dim_member') }} as d on s.member_key = d.member_key
    left join {{ ref('dim_member_year') }} as y
        on s.member_key = y.member_key and extract(year from s.discharge_dt) = y.year
    left join {{ ref('dim_member_year') }} as f
        on s.member_key = f.member_key and extract(year from s.discharge_dt + 30) = f.year
)

select
    *,
    case
        when exclude_invalid_dates then '01_invalid_dates'
        when exclude_unordered_member then '02_unordered_member'
        when exclude_header_conflict then '03_header_conflict'
        when exclude_performance_year then '04_outside_performance_year'
        when exclude_death_before_discharge then '05_death_on_or_before_discharge'
        when exclude_incomplete_data then '06_incomplete_data_window'
        when exclude_death_in_followup then '07_death_in_followup'
        when exclude_index_ffs then '08_index_ffs_proxy'
        when exclude_followup_ffs then '09_followup_ffs_proxy'
        else null
    end as exclusion_reason
from flags
