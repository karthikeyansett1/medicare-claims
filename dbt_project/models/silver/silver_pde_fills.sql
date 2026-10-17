select
    *,
    _sample_id::text || ':' || member_id || ':' || pde_id as fill_id
from {{ ref('stg_pde') }}
