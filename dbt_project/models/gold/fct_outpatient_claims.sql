{{ gold_config([{'columns':['outpatient_claim_id'],'unique':true}, {'columns':['member_key']}, {'columns':['member_id']}]) }}
select
    episode_id as outpatient_claim_id, {{ member_key() }} as member_key,
    _sample_id, member_id, claim_id, facility_id, service_start_dt as service_dt, service_end_dt,
    paid_amt, is_ed_visit, principal_dx_cd, segment_count, canonical_segment,
    has_header_conflict, repeated_equal_payment, has_negative_payment, missing_payment_segments,
    _source_file, _loaded_at
from {{ ref('silver_outpatient_claims') }}
