{% macro empty_string_to_null(value) -%}
    nullif(btrim(cast({{ value }} as text)), '')
{%- endmacro %}
