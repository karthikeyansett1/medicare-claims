{{ gold_config([{'columns':['member_key'],'unique':true}, {'columns':['member_id']}]) }}
with ranked as (
 select *, row_number() over(partition by _sample_id,member_id order by year desc) as recency
 from {{ ref('silver_member_months') }}
), history as (
 select _sample_id,member_id,min(year) as first_observed_year,max(year) as last_observed_year,
 min(death_dt) as death_dt,count(distinct death_dt)>1 as death_date_conflict,
 (count(distinct birth_dt)>1 or count(distinct sex_cd)>1 or count(distinct state_cd)>1) as has_demographic_variation
 from ranked group by _sample_id,member_id
)
select {{ member_key('h._sample_id','h.member_id') }} as member_key,
 h._sample_id,h.member_id,r.birth_dt,r.sex_cd,r.bene_race_cd as race_cd,r.state_cd,
 h.death_dt,h.first_observed_year,h.last_observed_year,r.year as canonical_year,
 h.death_date_conflict,h.has_demographic_variation
from history h join ranked r using (_sample_id,member_id) where r.recency=1
