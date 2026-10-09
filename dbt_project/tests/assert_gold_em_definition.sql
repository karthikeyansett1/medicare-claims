select claim_line_id from {{ ref('fct_professional_lines') }}
where is_office_em is distinct from coalesce(hcpcs_cd in
 ('99201','99202','99203','99204','99205','99211','99212','99213','99214','99215'),false)
