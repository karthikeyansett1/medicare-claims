{% macro facility_claims(kind) %}
with ranked as (
 select *, row_number() over (partition by _sample_id,member_id,claim_id
   order by segment nulls last, _source_file) as header_rank
 from {{ ref('stg_' ~ kind) }}
), totals as (
 select _sample_id,member_id,claim_id,count(*) as segment_count,
 sum(paid_amt) as paid_amt, count(*) filter(where paid_amt is null) as missing_payment_segments,
 bool_or(paid_amt < 0) as has_negative_payment,
 min(claim_from_dt) as service_start_dt,max(claim_thru_dt) as service_end_dt,
 {% for field in ['facility_id','icd9_dgns_cd_1','drg_cd','admit_dt','discharge_dt'] if kind == 'inpatient' or field in ['facility_id','icd9_dgns_cd_1'] %}
 (count(distinct {{ field }}) + case when count(*) filter(where {{ field }} is null)>0 then 1 else 0 end > 1)
 as {{ field }}_conflict,
 {% endfor %}
 (count(*) > 1 and count(distinct paid_amt)=1 and count(paid_amt)=count(*)) as repeated_equal_payment,
 {% if kind == 'outpatient' %}
 bool_or(false {% for n in range(1,46) %}or coalesce(hcpcs_cd_{{ n }} in ('99281','99282','99283','99284','99285'),false){% endfor %}) as is_ed_visit,
 {% endif %}
 array_agg(segment order by segment) as source_segments
 from ranked group by _sample_id,member_id,claim_id
)
select t.*, t._sample_id::text || ':' || t.member_id || ':' || t.claim_id as episode_id,
 h.facility_id,h.icd9_dgns_cd_1 as principal_dx_cd,
 {% if kind == 'inpatient' %}h.admit_dt,h.discharge_dt,h.drg_cd,{% endif %}
 h.segment as canonical_segment,h._source_file,h._loaded_at,
 (t.facility_id_conflict or t.icd9_dgns_cd_1_conflict
 {% if kind == 'inpatient' %}or t.admit_dt_conflict or t.discharge_dt_conflict or t.drg_cd_conflict{% endif %}) as has_header_conflict
from totals t join ranked h using (_sample_id,member_id,claim_id)
where h.header_rank=1
{% endmacro %}
