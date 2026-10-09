-- Segment-position grain prevents conflicting segment diagnoses from being erased.
{% for kind, size in [('inpatient',10),('outpatient',10),('carrier',8)] %}
select c._sample_id, c.member_id, c.claim_id, '{{ kind }}'::text as claim_type,
 {% if kind == 'carrier' %}null::integer{% else %}c.segment{% endif %} as segment,
 d.dx_position, upper(replace(d.icd9_dx_cd,'.','')) as icd9_dx_cd,
 d.icd9_dx_cd as source_dx_cd, c.claim_from_dt as service_dt, c._source_file, c._loaded_at
from {{ ref('stg_' ~ kind) }} c
cross join lateral (values
{% for n in range(1,size+1) %}
 ({{ n }}, c.icd9_dgns_cd_{{ n }}){% if not loop.last %},{% endif %}
{% endfor %}
) d(dx_position,icd9_dx_cd)
where d.icd9_dx_cd is not null
{% if not loop.last %}union all{% endif %}
{% endfor %}
