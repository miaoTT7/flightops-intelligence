select source_file_id, source_row_number, field_name, raw_value
from {{ source('bts_raw', 'bts_on_time_performance') }}
cross join lateral (
    values
        ('origin_state_fips', origin_state_fips),
        ('dest_state_fips', dest_state_fips)
) as fields(field_name, raw_value)
where nullif(btrim(raw_value), '') is not null
  and btrim(raw_value) !~ '^[0-9]{2}$'
