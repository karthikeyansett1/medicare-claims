{{ gold_config([{'columns':['icd9_dx_cd'],'unique':true}]) }}
select
    icd9_dx_cd,
    ccs_category,
    ccs_label
from {{ ref('ccs_dx_map') }}
