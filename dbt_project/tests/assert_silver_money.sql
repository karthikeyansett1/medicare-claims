with carrier_wide as (
 select sum({% for n in range(1,14) %}coalesce(line_nch_pmt_amt_{{ n }},0){% if not loop.last %}+{% endif %}{% endfor %}) as paid,
 sum({% for n in range(1,14) %}coalesce(line_alowd_chrg_amt_{{ n }},0){% if not loop.last %}+{% endif %}{% endfor %}) as allowed
 from {{ ref('stg_carrier') }}
)
select 'carrier' as failed_source from carrier_wide
where paid is distinct from (select sum(line_paid_amt) from {{ ref('silver_carrier_lines') }})
or allowed is distinct from (select sum(line_allowed_amt) from {{ ref('silver_carrier_lines') }})
{% for kind,model in [('inpatient','silver_inpatient_stays'),('outpatient','silver_outpatient_claims')] %}
union all select '{{ kind }}' where
 (select sum(paid_amt) from {{ ref('stg_' ~ kind) }}) is distinct from
 (select sum(paid_amt) from {{ ref(model) }})
{% endfor %}
{% for col in ['gross_drug_cost_amt','patient_pay_amt'] %}
union all select '{{ col }}' where
 (select sum({{ col }}) from {{ ref('stg_pde') }}) is distinct from
 (select sum({{ col }}) from {{ ref('silver_pde_fills') }})
{% endfor %}
{% for prefix,out in [('line_bene_ptb_ddctbl_amt','line_deductible_amt'),('line_bene_prmry_pyr_pd_amt','line_primary_payer_amt'),('line_coinsrnc_amt','line_coinsurance_amt')] %}
union all select '{{ out }}' where
 (select sum({% for n in range(1,14) %}coalesce({{ prefix }}_{{ n }},0){% if not loop.last %}+{% endif %}{% endfor %}) from {{ ref('stg_carrier') }})
 is distinct from (select sum({{ out }}) from {{ ref('silver_carrier_lines') }})
{% endfor %}
