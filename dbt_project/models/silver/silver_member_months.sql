-- Annual enrollment counts are not a reconstruction of monthly enrollment dates.
with annual as (
 select *, _file_year as year,
 case when death_dt < make_date(_file_year,1,1) then 0
      when extract(year from death_dt)=_file_year then extract(month from death_dt)::integer
      else 12 end as required_months,
 extract(year from age(make_date(_file_year,1,1),birth_dt))::integer as age_at_year_start
 from {{ ref('stg_beneficiary') }}
)
select *, {{ ffs_eligible() }} as is_ffs_eligible,
 (part_a_months=12 and part_b_months=12 and hmo_months=0) as is_full_year_ffs,
 'annual_count_proxy_including_death_month'::text as eligibility_method
from annual
