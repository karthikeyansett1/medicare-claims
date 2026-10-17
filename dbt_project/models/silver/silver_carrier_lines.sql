select
    c._sample_id::text || ':' || c.member_id || ':' || c.claim_id || ':' || l.line_num::text as claim_line_id,
    c._sample_id,
    c.member_id,
    c.claim_id,
    c.claim_from_dt,
    c.claim_thru_dt,
    l.*,
    c._source_file,
    c._loaded_at,
    l.rendering_npi is null as missing_rendering_npi,
    l.hcpcs_cd is null as missing_hcpcs,
    coalesce(l.line_paid_amt < 0, false) as has_negative_payment
from {{ ref('stg_carrier') }} as c
cross join
    lateral (
        values
        {% for n in range(1,14) %}
            (
                {{ n }}, c.prf_physn_npi_{{ n }}, c.tax_num_{{ n }}, c.hcpcs_cd_{{ n }},
                c.line_nch_pmt_amt_{{ n }}, c.line_alowd_chrg_amt_{{ n }}, c.line_icd9_dgns_cd_{{ n }},
                c.line_bene_ptb_ddctbl_amt_{{ n }}, c.line_bene_prmry_pyr_pd_amt_{{ n }},
                c.line_coinsrnc_amt_{{ n }}, c.line_prcsg_ind_cd_{{ n }}
            ){% if not loop.last %},{% endif %}
        {% endfor %}
    )
        as l (
            line_num, rendering_npi, tax_num, hcpcs_cd, line_paid_amt, line_allowed_amt, line_dx_cd,
            line_deductible_amt, line_primary_payer_amt, line_coinsurance_amt, line_processing_cd
        )
where {{ carrier_active() }}
