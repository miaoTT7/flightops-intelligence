with boolean_values as (
    select
        source_file_id,
        source_row_number,
        field_name,
        btrim(raw_value) as raw_value
    from {{ source('bts_raw', 'bts_on_time_performance') }}
    cross join lateral (
        values
            ('dep_del15', dep_del15),
            ('arr_del15', arr_del15),
            ('cancelled', cancelled),
            ('diverted', diverted),
            ('div_reached_dest', div_reached_dest)
    ) as fields(field_name, raw_value)
    where nullif(btrim(raw_value), '') is not null
)

select source_file_id, source_row_number, field_name, raw_value
from boolean_values
where raw_value !~ '^[01]([.]0+)?$'
