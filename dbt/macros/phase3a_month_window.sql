{% macro phase3a_month_window() -%}
    {%- set start_text = var('phase3a_batch_start_date', '') -%}
    {%- set end_text = var('phase3a_batch_end_date', '') -%}
    {%- if not modules.re.match('^\d{4}-\d{2}-01$', start_text) -%}
        {{ exceptions.raise_compiler_error('phase3a_batch_start_date must be YYYY-MM-01') }}
    {%- endif -%}
    {%- if not modules.re.match('^\d{4}-\d{2}-01$', end_text) -%}
        {{ exceptions.raise_compiler_error('phase3a_batch_end_date must be YYYY-MM-01') }}
    {%- endif -%}
    {%- set start_date = modules.datetime.datetime.strptime(start_text, '%Y-%m-%d').date() -%}
    {%- set expected_end = (start_date.replace(day=28) + modules.datetime.timedelta(days=4)).replace(day=1) -%}
    {%- set end_date = modules.datetime.datetime.strptime(end_text, '%Y-%m-%d').date() -%}
    {%- if end_date != expected_end -%}
        {{ exceptions.raise_compiler_error('Phase 3A UTC batches must cover exactly one calendar month') }}
    {%- endif -%}
    {%- if flags.FULL_REFRESH -%}
        {{ exceptions.raise_compiler_error('Full refresh is disabled for int_flight_timestamps; use guarded monthly batches') }}
    {%- endif -%}
    {{ return({'start': start_text, 'end': end_text}) }}
{%- endmacro %}
