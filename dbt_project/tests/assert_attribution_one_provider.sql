{{ config(tags=['step7']) }}
select member_year_key, method
from {{ ref('attribution_long') }}
group by member_year_key, method
having count(*) <> 1 or count(distinct attributed_npi) > 1
