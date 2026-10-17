{{ config(tags=['step7']) }}
with expected as (
    select member_year_key, method
    from {{ ref('dim_member_year') }}
    cross join (values ('A_visits'), ('B_allowed')) as m(method)
    where is_ffs_eligible and year in (2009, 2010)
)
(select * from expected except select member_year_key, method from {{ ref('attribution_long') }})
union all
(select member_year_key, method from {{ ref('attribution_long') }} except select * from expected)
