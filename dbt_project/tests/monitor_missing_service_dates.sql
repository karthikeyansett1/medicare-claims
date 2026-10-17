{{ config(severity='warn', tags=['quality_monitor']) }}
{% for model,key,date in [('fct_professional_lines','claim_line_id','service_dt'),('fct_inpatient_stays','stay_id','service_dt'),('fct_outpatient_claims','outpatient_claim_id','service_dt'),('fct_rx_fills','fill_id','fill_dt')] %}
select '{{ model }}' as fact_type,{{ key }} as event_key from {{ ref(model) }}
where {{ date }} is null
{% if not loop.last %}union all{% endif %}
{% endfor %}
