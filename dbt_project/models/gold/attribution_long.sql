{{ gold_config([{'columns':['member_year_key','method'],'unique':true}, {'columns':['attributed_npi','year','method']}]) }}
{{ config(tags=['step7']) }}
select * from {{ ref('attribution_a') }}
union all
select * from {{ ref('attribution_b') }}
