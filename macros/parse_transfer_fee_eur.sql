{% macro parse_transfer_fee_eur(transfer_fee_column) %}
try_cast(regexp_extract({{ transfer_fee_column }}, '([0-9]+\\.?[0-9]*)', 1) as double)
* case
    when {{ transfer_fee_column }} rlike '(?i)M' then 1000000
    when {{ transfer_fee_column }} rlike '(?i)K' then 1000
    else 1
  end
{% endmacro %}
