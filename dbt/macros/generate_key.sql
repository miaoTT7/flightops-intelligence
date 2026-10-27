{% macro generate_key(fields) -%}
    {%- if fields | length == 0 -%}
        {{ exceptions.raise_compiler_error(
            'generate_key requires at least one field'
        ) }}
    {%- endif -%}

    md5(concat(
        {%- for field in fields %}
        case
            when {{ field }} is null then '-1:'
            else length(cast({{ field }} as text))::text
                 || ':' || cast({{ field }} as text)
        end{% if not loop.last %}, {% endif %}
        {%- endfor %}
    ))
{%- endmacro %}
