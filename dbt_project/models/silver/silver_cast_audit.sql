{% for table, cols in var('source_columns').items() %}
select '{{ table }}'::text as source_table, _source_file,
  count(*) as source_rows,
  count(*) filter (where cardinality(_cast_error_columns) > 0) as rows_with_cast_errors,
  coalesce(sum(cardinality(_cast_error_columns)),0) as cast_error_values
from {{ ref('stg_' ~ table) }} group by _source_file
{% if not loop.last %}union all{% endif %}
{% endfor %}
