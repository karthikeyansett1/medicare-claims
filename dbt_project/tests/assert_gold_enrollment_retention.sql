select y.member_year_key from {{ ref('dim_member_year') }} y
left join {{ ref('fct_member_year_cost') }} c using(member_year_key)
where c.cost_year_key is null or not c.has_annual_enrollment
union all
select c.cost_year_key from {{ ref('fct_member_year_cost') }} c
where c.has_annual_enrollment is distinct from (c.member_year_key is not null)
