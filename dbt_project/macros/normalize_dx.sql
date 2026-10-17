{% macro normalize_dx(expression) %}
nullif(upper(replace(trim({{ expression }}), '.', '')), '')
{% endmacro %}
