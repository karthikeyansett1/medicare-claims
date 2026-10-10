-- Baseline overall unmatched 0.0529%; alert if any claim type exceeds 2%.
select claim_type
from {{ ref('silver_diagnoses_grouped') }}
group by claim_type
having count(*) filter (where not is_ccs_mapped)::numeric / nullif(count(*), 0) > 0.02
