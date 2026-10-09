{% macro carrier_active(alias='l') -%}
({{ alias }}.hcpcs_cd is not null or {{ alias }}.rendering_npi is not null
 or {{ alias }}.line_dx_cd is not null
 or coalesce({{ alias }}.line_paid_amt,0) <> 0
 or coalesce({{ alias }}.line_allowed_amt,0) <> 0)
{%- endmacro %}
