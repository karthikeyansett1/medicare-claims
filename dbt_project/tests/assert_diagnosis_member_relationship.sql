select d._sample_id,d.member_id
from {{ ref('silver_diagnoses') }} d
left join {{ ref('dim_member') }} m on d._sample_id=m._sample_id and d.member_id=m.member_id
where m.member_key is null
group by d._sample_id,d.member_id
