with compared as (
    select
        staging.flight_record_key,
        time_field,
        nullif(btrim(raw_value), '') as raw_value,
        converted_time,
        day_offset
    from {{ source('bts_raw', 'bts_on_time_performance') }} as raw
    inner join {{ ref('stg_bts_flights') }} as staging
        using (source_file_id, source_row_number)
    cross join lateral (
        values
            ('crs_dep_time', raw.crs_dep_time, staging.scheduled_departure_time, staging.scheduled_departure_day_offset),
            ('dep_time', raw.dep_time, staging.actual_departure_time, staging.actual_departure_day_offset),
            ('wheels_off', raw.wheels_off, staging.wheels_off_time, staging.wheels_off_day_offset),
            ('wheels_on', raw.wheels_on, staging.wheels_on_time, staging.wheels_on_day_offset),
            ('crs_arr_time', raw.crs_arr_time, staging.scheduled_arrival_time, staging.scheduled_arrival_day_offset),
            ('arr_time', raw.arr_time, staging.actual_arrival_time, staging.actual_arrival_day_offset),
            ('first_dep_time', raw.first_dep_time, staging.first_departure_time, staging.first_departure_day_offset)
    ) as times(time_field, raw_value, converted_time, day_offset)
)

select flight_record_key, time_field, raw_value, converted_time, day_offset
from compared
where case
    when raw_value is null then converted_time is not null or day_offset is not null
    when raw_value = '2400' then converted_time is distinct from time '00:00:00' or day_offset is distinct from 1
    else converted_time is null or day_offset is distinct from 0
end
