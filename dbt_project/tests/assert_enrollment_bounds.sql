select member_id,_file_year from {{ ref('silver_member_months') }} where
{% for c in ['part_a_months','part_b_months','hmo_months','part_d_months'] %}
{{ c }} not between 0 and 12 {% if not loop.last %}or{% endif %}
{% endfor %}
