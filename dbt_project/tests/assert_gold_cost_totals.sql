{% for fact,col,summary_col in [
 ('fct_inpatient_stays','paid_amt','inpatient_paid_amt'),
 ('fct_outpatient_claims','paid_amt','outpatient_paid_amt'),
 ('fct_professional_lines','paid_amt','professional_paid_amt'),
 ('fct_professional_lines','allowed_amt','professional_allowed_amt'),
 ('fct_rx_fills','gross_drug_cost_amt','rx_gross_cost_amt'),
 ('fct_rx_fills','patient_pay_amt','rx_patient_pay_amt')] %}
select '{{ summary_col }}' as failed_measure where
 (select sum({{ col }}) from {{ ref(fact) }}) is distinct from
 (select sum({{ summary_col }}) from {{ ref('fct_member_year_cost') }})
{% if not loop.last %}union all{% endif %}
{% endfor %}
union all select 'medical_definition' where exists (
 select 1 from {{ ref('fct_member_year_cost') }} where medical_paid_amt <>
 inpatient_paid_amt+outpatient_paid_amt+professional_paid_amt)
