select
    d.*,
    c.ccs_category,
    c.ccs_label,
    c.icd9_dx_cd is not null as is_ccs_mapped
from {{ ref('silver_diagnoses') }} as d
left join {{ ref('dim_dx_ccs') }} as c
    on {{ normalize_dx('d.icd9_dx_cd') }} = c.icd9_dx_cd
