{{ gold_config([{'columns':['member_year_key'],'unique':true}, {'columns':['attributed_npi','year']}]) }}
{{ config(tags=['step7']) }}
with ranked as (
    select
        *,
        row_number()
            over (partition by member_year_key order by known_allowed_amt desc, service_days desc, rendering_npi)
            as candidate_rank,
        count(*) over (partition by member_year_key) as candidate_count,
        count(*) over (partition by member_year_key, known_allowed_amt) as primary_score_tie_count,
        count(*) over (partition by member_year_key, known_allowed_amt, service_days) as final_score_tie_count
    from {{ ref('attribution_candidates') }}
    where known_allowed_lines > 0
)

select
    e.member_year_key,
    e.member_key,
    e._sample_id,
    e.member_id,
    e.year,
    'B_allowed'::text as method,
    r.rendering_npi as attributed_npi,
    (r.rendering_npi is not null) as is_attributed,
    r.office_visit_days,
    r.last_office_visit,
    r.service_days,
    r.known_allowed_amt,
    r.known_allowed_lines,
    r.missing_allowed_lines,
    coalesce(r.candidate_count, 0) as candidate_count,
    coalesce(r.primary_score_tie_count, 0) as primary_score_tie_count,
    coalesce(r.final_score_tie_count, 0) as final_score_tie_count
from {{ ref('dim_member_year') }} as e
left join ranked as r on e.member_year_key = r.member_year_key and r.candidate_rank = 1
where e.is_ffs_eligible and e.year in (2009, 2010)
