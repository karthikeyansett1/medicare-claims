{{ gold_config([{'columns':['member_year_key','rendering_npi'],'unique':true}]) }}
{{ config(tags=['step7']) }}
select
    e.member_year_key,
    e.member_key,
    e._sample_id,
    e.member_id,
    e.year,
    f.rendering_npi,
    count(*) as professional_lines,
    count(distinct f.service_dt) as service_days,
    count(distinct f.service_dt) filter (where f.is_office_em) as office_visit_days,
    max(f.service_dt) filter (where f.is_office_em) as last_office_visit,
    sum(f.allowed_amt) as known_allowed_amt,
    count(f.allowed_amt) as known_allowed_lines,
    count(*) filter (where f.allowed_amt is null) as missing_allowed_lines
from {{ ref('dim_member_year') }} as e
inner join {{ ref('fct_professional_lines') }} as f
    on e.member_key = f.member_key and e.year = extract(year from f.service_dt)::integer
where e.is_ffs_eligible and e.year in (2009, 2010) and f.rendering_npi is not null
group by e.member_year_key, e.member_key, e._sample_id, e.member_id, e.year, f.rendering_npi
