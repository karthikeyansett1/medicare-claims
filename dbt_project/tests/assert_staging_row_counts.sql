{% for table in var('source_columns') %}
select '{{ table }}' as source_table
where (select count(*) from {{ source('bronze',table) }}) <>
      (select count(*) from {{ ref('stg_' ~ table) }})
{% if not loop.last %}union all{% endif %}
{% endfor %}
