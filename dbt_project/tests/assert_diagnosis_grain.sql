select _sample_id,member_id,claim_id,claim_type,segment,dx_position,count(*)
from {{ ref('silver_diagnoses') }} group by 1,2,3,4,5,6 having count(*)>1
or member_id is null or claim_id is null or dx_position is null or _sample_id is null
