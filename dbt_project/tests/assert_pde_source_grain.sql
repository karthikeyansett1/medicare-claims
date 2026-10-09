select _sample_id,member_id,pde_id, count(*) from {{ ref('stg_pde') }} group by _sample_id,member_id,pde_id having count(*) > 1 or _sample_id is null or member_id is null or pde_id is null
