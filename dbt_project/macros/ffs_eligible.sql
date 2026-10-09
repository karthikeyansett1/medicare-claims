{% macro ffs_eligible() -%}
(part_a_months between required_months and 12
 and part_b_months between required_months and 12 and hmo_months = 0
 and required_months between 1 and 12)
{%- endmacro %}
