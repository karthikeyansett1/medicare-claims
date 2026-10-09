{% for src,dst,src_cols,dst_cols in [
 ('silver_carrier_lines','fct_professional_lines',['line_paid_amt','line_allowed_amt'],['paid_amt','allowed_amt']),
 ('silver_inpatient_stays','fct_inpatient_stays',['paid_amt'],['paid_amt']),
 ('silver_outpatient_claims','fct_outpatient_claims',['paid_amt'],['paid_amt']),
 ('silver_pde_fills','fct_rx_fills',['gross_drug_cost_amt','patient_pay_amt'],['gross_drug_cost_amt','patient_pay_amt'])] %}
select '{{ dst }}'::text as failed_model where
 (select count(*) from {{ ref(src) }}) <> (select count(*) from {{ ref(dst) }})
{% for c in src_cols %}
 or (select sum({{ c }}) from {{ ref(src) }}) is distinct from
 (select sum({{ dst_cols[loop.index0] }}) from {{ ref(dst) }})
{% endfor %}
{% if not loop.last %}union all{% endif %}
{% endfor %}
