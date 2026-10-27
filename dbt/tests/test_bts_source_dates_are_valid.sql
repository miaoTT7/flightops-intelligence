with source_values as (
    select
        source_file_id,
        source_row_number,
        btrim(flight_date) as raw_value
    from {{ source('bts_raw', 'bts_on_time_performance') }}
    where nullif(btrim(flight_date), '') is not null
),

validated as (
    select
        *,
        pg_input_is_valid(raw_value, 'date') as is_valid_date
    from source_values
)

select source_file_id, source_row_number, raw_value
from validated
where raw_value !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
   or case
        when not is_valid_date then true
        else to_char(raw_value::date, 'YYYY-MM-DD') <> raw_value
      end
