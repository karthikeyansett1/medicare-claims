{{ config(severity='warn', tags=['quality_monitor']) }}
-- Missing dates are monitored separately; a NULL date cannot prove timeliness.
{% for model,key,date in [('fct_professional_lines','claim_line_id','service_dt'),('fct_inpatient_stays','stay_id','service_dt'),('fct_outpatient_claims','outpatient_claim_id','service_dt'),('fct_rx_fills','fill_id','fill_dt')] %}
select '{{ model }}' as fact_type,f.{{ key }} as event_key,f.{{ date }} as service_dt,m.death_dt
from {{ ref(model) }} f join {{ ref('dim_member') }} m using(member_key)
where {{ after_death_threshold('f.' ~ date,'m.death_dt') }}
{% if not loop.last %}union all{% endif %}
{% endfor %}
