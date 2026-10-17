-- Canonical principal diagnosis assigns every stay exactly once, including unknowns.
select
    extract(year from f.admit_dt)::integer as year,
    coalesce(c.ccs_category, 'UNMAPPED') as ccs_category,
    coalesce(c.ccs_label, 'Unmapped or missing principal diagnosis') as ccs_label,
    count(distinct f.member_key) as member_count,
    count(*) as inpatient_stays,
    sum(f.paid_amt) as inpatient_paid,
    count(*) filter (where f.paid_amt is null) as missing_payment_stays
from {{ ref('fct_inpatient_stays') }} as f
left join {{ ref('dim_dx_ccs') }} as c
    on {{ normalize_dx('f.principal_dx_cd') }} = c.icd9_dx_cd
group by 1, 2, 3
