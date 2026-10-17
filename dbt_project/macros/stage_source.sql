{% macro stage_source(table) %}
{% set columns = var('source_columns')[table] %}
select
{% for c in columns %}
  {{ typed_value(c.source, c.kind) }} as {{ c.name }},
{% endfor %}
  _sample_id, _file_year, _source_file, _loaded_at,
  array_remove(array[
{% for c in columns if c.kind != 'text' %}
    case when {{ clean_text(c.source) }} is not null
      and ({{ typed_value(c.source, c.kind) }}) is null then '{{ c.source }}'::text end
    {% if not loop.last %},{% endif %}
{% endfor %}
  ], null) as _cast_error_columns
from {{ source('bronze', table) }}
{% endmacro %}
