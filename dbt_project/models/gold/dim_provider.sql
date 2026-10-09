{{ gold_config([{'columns':['provider_key'],'unique':true}, {'columns':['npi']}]) }}
with appearances as (
 select _sample_id,rendering_npi as npi,min(service_dt) as first_seen_dt,
 count(*) as total_lines_billed,bool_or(is_office_em) as is_em_provider,
 true as seen_as_rendering,false as seen_as_inpatient_attending
 from {{ ref('fct_professional_lines') }} where rendering_npi is not null
 group by _sample_id,rendering_npi
 union all
 select _sample_id,attending_npi as npi,min(service_dt),0::bigint,false,false,true
 from {{ ref('fct_inpatient_stays') }} where attending_npi is not null
 group by _sample_id,attending_npi
)
select {{ provider_key('_sample_id','npi') }} as provider_key,_sample_id,npi,
 min(first_seen_dt) as first_seen_dt,sum(total_lines_billed)::bigint as total_lines_billed,
 bool_or(is_em_provider) as is_em_provider,bool_or(seen_as_rendering) as seen_as_rendering,
 bool_or(seen_as_inpatient_attending) as seen_as_inpatient_attending
from appearances group by _sample_id,npi
