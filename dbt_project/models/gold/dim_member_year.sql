{{ gold_config([{'columns':['member_year_key'],'unique':true}, {'columns':['member_key','year'],'unique':true}, {'columns':['member_id','year']}]) }}
select {{ member_key() }} || ':' || year::text as member_year_key,
 {{ member_key() }} as member_key,_sample_id,member_id,year,
 birth_dt,death_dt,sex_cd,state_cd,bene_race_cd as race_cd,
 part_a_months,part_b_months,hmo_months,part_d_months,
 required_months,age_at_year_start,is_full_year_ffs,is_ffs_eligible,eligibility_method,
sp_alzhdmta,
sp_chf,
sp_chrnkidn,
sp_cncr,
sp_copd,
sp_depressn,
sp_diabetes,
sp_ischmcht,
sp_osteoprs,
sp_ra_oa,
sp_strketia,
 case when sp_alzhdmta is null or sp_chf is null or sp_chrnkidn is null or sp_cncr is null or sp_copd is null or sp_depressn is null or sp_diabetes is null or sp_ischmcht is null or sp_osteoprs is null or sp_ra_oa is null or sp_strketia is null then null else
 sp_alzhdmta::integer + sp_chf::integer + sp_chrnkidn::integer + sp_cncr::integer + sp_copd::integer + sp_depressn::integer + sp_diabetes::integer + sp_ischmcht::integer + sp_osteoprs::integer + sp_ra_oa::integer + sp_strketia::integer end as chronic_condition_count,
 (sp_alzhdmta is null)::integer + (sp_chf is null)::integer + (sp_chrnkidn is null)::integer + (sp_cncr is null)::integer + (sp_copd is null)::integer + (sp_depressn is null)::integer + (sp_diabetes is null)::integer + (sp_ischmcht is null)::integer + (sp_osteoprs is null)::integer + (sp_ra_oa is null)::integer + (sp_strketia is null)::integer as chronic_flag_missing_count
from {{ ref('silver_member_months') }}
