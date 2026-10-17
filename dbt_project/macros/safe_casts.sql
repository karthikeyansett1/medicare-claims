{% macro clean_text(col) -%}nullif(btrim({{ col }}), ''){%- endmacro %}

{% macro safe_numeric(col) -%}
case when length({{ clean_text(col) }}) <= 30
 and {{ clean_text(col) }} ~ '^-?[0-9]+(\.[0-9]+)?$'
 then {{ clean_text(col) }}::numeric end
{%- endmacro %}

{% macro safe_integer(col) -%}
case when {{ clean_text(col) }} ~ '^[0-9]{1,9}$'
 then {{ clean_text(col) }}::integer end
{%- endmacro %}

{% macro safe_date(col) -%}
case when {{ clean_text(col) }} ~ '^[0-9]{8}$' then
 case when substring({{ clean_text(col) }},1,4)::int between 1 and 9999
       and substring({{ clean_text(col) }},5,2)::int between 1 and 12 then
  case when substring({{ clean_text(col) }},7,2)::int between 1 and
    extract(day from (make_date(substring({{ clean_text(col) }},1,4)::int,
       substring({{ clean_text(col) }},5,2)::int,1) + interval '1 month - 1 day'))::int
   then make_date(substring({{ clean_text(col) }},1,4)::int,
       substring({{ clean_text(col) }},5,2)::int,substring({{ clean_text(col) }},7,2)::int)
  end
 end
end
{%- endmacro %}

{% macro safe_flag(col) -%}
case {{ clean_text(col) }} when '1' then true when '2' then false end
{%- endmacro %}

{% macro typed_value(col, kind) -%}
{% if kind == 'date' %}{{ safe_date(col) }}
{% elif kind == 'numeric' %}{{ safe_numeric(col) }}
{% elif kind == 'integer' %}{{ safe_integer(col) }}
{% elif kind == 'flag' %}{{ safe_flag(col) }}
{% else %}{{ clean_text(col) }}{% endif %}
{%- endmacro %}
