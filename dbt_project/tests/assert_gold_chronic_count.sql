{% set flags = ['sp_alzhdmta','sp_chf','sp_chrnkidn','sp_cncr','sp_copd','sp_depressn','sp_diabetes','sp_ischmcht','sp_osteoprs','sp_ra_oa','sp_strketia'] %}
select member_year_key from {{ ref('dim_member_year') }}
where chronic_flag_missing_count not between 0 and 11
 or (chronic_flag_missing_count > 0 and chronic_condition_count is not null)
 or (chronic_flag_missing_count = 0 and chronic_condition_count is distinct from
 ({% for f in flags %}case when {{ f }} then 1 else 0 end{% if not loop.last %}+{% endif %}{% endfor %}))
