with hhmm_values as (
    select
        source_file_id,
        source_row_number,
        field_name,
        btrim(raw_value) as raw_value
    from {{ source('bts_raw', 'bts_on_time_performance') }}
    cross join lateral (
        values
            ('crs_dep_time', crs_dep_time),
            ('dep_time', dep_time),
            ('wheels_off', wheels_off),
            ('wheels_on', wheels_on),
            ('crs_arr_time', crs_arr_time),
            ('arr_time', arr_time),
            ('first_dep_time', first_dep_time)
    ) as fields(field_name, raw_value)
    where nullif(btrim(raw_value), '') is not null
),

validated as (
    select
        *,
        pg_input_is_valid(raw_value, 'integer') as is_integer
    from hhmm_values
)

select source_file_id, source_row_number, field_name, raw_value
from validated
where raw_value !~ '^[0-9]{1,4}$'
   or case
        when not is_integer then true
        else not (
            raw_value::integer = 2400
            or (
                raw_value::integer between 0 and 2359
                and mod(raw_value::integer, 100) between 0 and 59
            )
        )
      end
