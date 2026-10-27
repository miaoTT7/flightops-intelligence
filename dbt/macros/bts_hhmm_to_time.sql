{% macro bts_hhmm_to_time(value, part='time') -%}
    {%- if part not in ['time', 'day_offset'] -%}
        {{ exceptions.raise_compiler_error(
            "bts_hhmm_to_time part must be 'time' or 'day_offset'"
        ) }}
    {%- endif -%}

    {%- set cleaned_value -%}
        btrim(cast({{ value }} as text))
    {%- endset -%}

    case
        when {{ value }} is null then null
        when {{ cleaned_value }} !~ '^[0-9]{1,4}$' then null
        when cast({{ cleaned_value }} as integer) = 2400 then
            {%- if part == 'time' %} time '00:00:00'
            {%- else %} 1
            {%- endif %}
        when cast({{ cleaned_value }} as integer) between 0 and 2359
             and mod(cast({{ cleaned_value }} as integer), 100) between 0 and 59
        then
            {%- if part == 'time' %}
                make_time(
                    cast({{ cleaned_value }} as integer) / 100,
                    mod(cast({{ cleaned_value }} as integer), 100),
                    0
                )
            {%- else %} 0
            {%- endif %}
        else null
    end
{%- endmacro %}
