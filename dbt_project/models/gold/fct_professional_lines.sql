{{ gold_config([{'columns':['claim_line_id'],'unique':true}, {'columns':['member_key']}, {'columns':['member_id']}, {'columns':['rendering_npi','service_dt']}]) }}
select l.claim_line_id,{{ member_key('l._sample_id','l.member_id') }} as member_key,
 {{ provider_key('l._sample_id','l.rendering_npi') }} as provider_key,
 l._sample_id,l.member_id,l.claim_id,l.line_num,l.rendering_npi,
 l.claim_from_dt as service_dt,l.claim_thru_dt as service_end_dt,
 l.hcpcs_cd,l.line_paid_amt as paid_amt,l.line_allowed_amt as allowed_amt,
 l.line_dx_cd, (e.hcpcs_cd is not null) as is_office_em,
 l.missing_rendering_npi,l.missing_hcpcs,l.has_negative_payment,
 l._source_file,l._loaded_at
from {{ ref('silver_carrier_lines') }} l
left join {{ ref('em_office_visit_codes') }} e on l.hcpcs_cd=e.hcpcs_cd
