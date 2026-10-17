select _sample_id,member_id,claim_id, count(*) from {{ ref('stg_carrier') }} group by _sample_id,member_id,claim_id having count(*) > 1 or _sample_id is null or member_id is null or claim_id is null
