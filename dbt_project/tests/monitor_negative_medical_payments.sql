{{ config(severity='warn', tags=['quality_monitor']) }}
-- Negative source payments are preserved adjustments, not universal corruption.
{% for model,key in [('fct_professional_lines','claim_line_id'),('fct_inpatient_stays','stay_id'),('fct_outpatient_claims','outpatient_claim_id')] %}
select '{{ model }}' as fact_type,{{ key }} as event_key from {{ ref(model) }}
where has_negative_payment
{% if not loop.last %}union all{% endif %}
{% endfor %}
