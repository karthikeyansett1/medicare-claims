{{ gold_config([{'columns':['stay_id'],'unique':true}, {'columns':['member_key']}, {'columns':['member_id']}]) }}
select s.episode_id as stay_id,{{ member_key('s._sample_id','s.member_id') }} as member_key,
 {{ provider_key('s._sample_id','h.at_physn_npi') }} as attending_provider_key,
 s._sample_id,s.member_id,s.claim_id,s.facility_id,h.at_physn_npi as attending_npi,
 s.admit_dt,s.discharge_dt,s.admit_dt as service_dt,s.service_start_dt,s.service_end_dt,
 s.paid_amt,s.drg_cd,s.principal_dx_cd,s.segment_count,s.canonical_segment,
 s.has_header_conflict,s.repeated_equal_payment,s.has_negative_payment,
 s.missing_payment_segments,s._source_file,s._loaded_at
from {{ ref('silver_inpatient_stays') }} s
left join {{ ref('stg_inpatient') }} h
 on s._sample_id=h._sample_id and s.member_id=h.member_id
 and s.claim_id=h.claim_id and s.canonical_segment=h.segment
