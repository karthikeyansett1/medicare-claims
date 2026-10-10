{{ config(severity='warn', tags=['quality_monitor']) }}
select 'inpatient' as claim_type,stay_id as event_key from {{ ref('fct_inpatient_stays') }} where has_header_conflict
union all
select 'outpatient' as claim_type,outpatient_claim_id as event_key from {{ ref('fct_outpatient_claims') }} where has_header_conflict
