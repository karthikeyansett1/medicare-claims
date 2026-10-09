{% macro member_key(sample='_sample_id', member='member_id') -%}
{{ sample }}::text || ':' || {{ member }}
{%- endmacro %}
{% macro provider_key(sample='_sample_id', npi='rendering_npi') -%}
{{ sample }}::text || ':' || {{ npi }}
{%- endmacro %}
{% macro gold_config(indexes) %}
{{ config(indexes=indexes, post_hook='analyze {{ this }}') }}
{% endmacro %}
