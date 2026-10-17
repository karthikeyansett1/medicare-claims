select * from {{ ref('silver_cast_audit') }} where cast_error_values <> 0
