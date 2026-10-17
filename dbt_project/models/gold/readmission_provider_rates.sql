{{ gold_config([{'columns':['_sample_id','attributed_npi','year','method'],'unique':true}]) }}
{{ config(tags=['step9']) }}
with panels as (
    select
        _sample_id,
        attributed_npi,
        year,
        method,
        count(*) as attributed_members
    from {{ ref('attribution_long') }}
    where attributed_npi is not null
    group by _sample_id, attributed_npi, year, method
),

events as (
    select
        a._sample_id,
        a.attributed_npi,
        a.year,
        a.method,
        count(*) as index_stays,
        count(*) filter (where r.is_readmit_30d) as readmissions
    from {{ ref('fct_readmissions') }} as r
    inner join {{ ref('attribution_long') }} as a on r.member_key = a.member_key and r.year = a.year
    where r.is_index_eligible and a.attributed_npi is not null
    group by a._sample_id, a.attributed_npi, a.year, a.method
)

select
    p.*,
    coalesce(e.index_stays, 0) as index_stays,
    coalesce(e.readmissions, 0) as readmissions,
    e.readmissions::numeric / nullif(e.index_stays, 0) as readmission_rate,
    p.attributed_members >= 20 as meets_panel_threshold
from panels as p left join events as e
    on
        p._sample_id = e._sample_id and p.attributed_npi = e.attributed_npi
        and p.year = e.year and p.method = e.method
