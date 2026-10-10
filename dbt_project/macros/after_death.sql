{% macro after_death_threshold(service_date, death_date) -%}
{{ service_date }} > {{ death_date }} + 30
{%- endmacro %}
