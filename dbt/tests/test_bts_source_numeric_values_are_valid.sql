with source_rows as (
    select *
    from {{ source('bts_raw', 'bts_on_time_performance') }}
),

numeric_values as (
    select
        source_file_id,
        source_row_number,
        field_name,
        btrim(raw_value) as raw_value,
        allowed_pattern,
        minimum_value,
        maximum_value
    from source_rows
    cross join lateral (
        values
            ('year', year, '^[0-9]{4}$', 0::numeric, 32767::numeric),
            ('quarter', quarter, '^[1-4]$', 1::numeric, 4::numeric),
            ('month', month, '^(0?[1-9]|1[0-2])$', 1::numeric, 12::numeric),
            ('day_of_month', day_of_month, '^([1-9]|[12][0-9]|3[01])$', 1::numeric, 31::numeric),
            ('day_of_week', day_of_week, '^[1-7]$', 1::numeric, 7::numeric),
            ('dot_id_reporting_airline', dot_id_reporting_airline, '^[0-9]+$', 0::numeric, 2147483647::numeric),
            ('origin_airport_id', origin_airport_id, '^[0-9]+$', 0::numeric, 2147483647::numeric),
            ('origin_airport_seq_id', origin_airport_seq_id, '^[0-9]+$', 0::numeric, 2147483647::numeric),
            ('origin_city_market_id', origin_city_market_id, '^[0-9]+$', 0::numeric, 2147483647::numeric),
            ('origin_wac', origin_wac, '^[0-9]+$', 0::numeric, 32767::numeric),
            ('dest_airport_id', dest_airport_id, '^[0-9]+$', 0::numeric, 2147483647::numeric),
            ('dest_airport_seq_id', dest_airport_seq_id, '^[0-9]+$', 0::numeric, 2147483647::numeric),
            ('dest_city_market_id', dest_city_market_id, '^[0-9]+$', 0::numeric, 2147483647::numeric),
            ('dest_wac', dest_wac, '^[0-9]+$', 0::numeric, 32767::numeric),
            ('dep_delay', dep_delay, '^[+-]?[0-9]+([.]0+)?$', -2147483648::numeric, 2147483647::numeric),
            ('dep_delay_minutes', dep_delay_minutes, '^[0-9]+([.]0+)?$', 0::numeric, 2147483647::numeric),
            ('departure_delay_groups', departure_delay_groups, '^[+-]?[0-9]+([.]0+)?$', -32768::numeric, 32767::numeric),
            ('taxi_out', taxi_out, '^[0-9]+([.]0+)?$', 0::numeric, 2147483647::numeric),
            ('taxi_in', taxi_in, '^[0-9]+([.]0+)?$', 0::numeric, 2147483647::numeric),
            ('arr_delay', arr_delay, '^[+-]?[0-9]+([.]0+)?$', -2147483648::numeric, 2147483647::numeric),
            ('arr_delay_minutes', arr_delay_minutes, '^[0-9]+([.]0+)?$', 0::numeric, 2147483647::numeric),
            ('arrival_delay_groups', arrival_delay_groups, '^[+-]?[0-9]+([.]0+)?$', -32768::numeric, 32767::numeric),
            ('crs_elapsed_time', crs_elapsed_time, '^[0-9]+([.]0+)?$', 0::numeric, 2147483647::numeric),
            ('actual_elapsed_time', actual_elapsed_time, '^[0-9]+([.]0+)?$', 0::numeric, 2147483647::numeric),
            ('air_time', air_time, '^[0-9]+([.]0+)?$', 0::numeric, 2147483647::numeric),
            ('flights', flights, '^[0-9]+([.]0+)?$', 0::numeric, 32767::numeric),
            ('distance', distance, '^[0-9]+([.][0-9]+)?$', 0::numeric, 99999999.99::numeric),
            ('distance_group', distance_group, '^[0-9]+([.]0+)?$', 0::numeric, 32767::numeric),
            ('carrier_delay', carrier_delay, '^[0-9]+([.]0+)?$', 0::numeric, 2147483647::numeric),
            ('weather_delay', weather_delay, '^[0-9]+([.]0+)?$', 0::numeric, 2147483647::numeric),
            ('nas_delay', nas_delay, '^[0-9]+([.]0+)?$', 0::numeric, 2147483647::numeric),
            ('security_delay', security_delay, '^[0-9]+([.]0+)?$', 0::numeric, 2147483647::numeric),
            ('late_aircraft_delay', late_aircraft_delay, '^[0-9]+([.]0+)?$', 0::numeric, 2147483647::numeric),
            ('total_add_g_time', total_add_g_time, '^[0-9]+([.]0+)?$', 0::numeric, 2147483647::numeric),
            ('longest_add_g_time', longest_add_g_time, '^[0-9]+([.]0+)?$', 0::numeric, 2147483647::numeric),
            ('div_airport_landings', div_airport_landings, '^[0-9]+$', 0::numeric, 32767::numeric),
            ('div_actual_elapsed_time', div_actual_elapsed_time, '^[0-9]+([.]0+)?$', 0::numeric, 2147483647::numeric),
            ('div_arr_delay', div_arr_delay, '^[+-]?[0-9]+([.]0+)?$', -2147483648::numeric, 2147483647::numeric),
            ('div_distance', div_distance, '^[0-9]+([.][0-9]+)?$', 0::numeric, 99999999.99::numeric)
    ) as fields(field_name, raw_value, allowed_pattern, minimum_value, maximum_value)
    where nullif(btrim(raw_value), '') is not null
),

validated as (
    select
        *,
        pg_input_is_valid(raw_value, 'numeric') as is_numeric
    from numeric_values
)

select source_file_id, source_row_number, field_name, raw_value
from validated
where raw_value !~ allowed_pattern
   or case
        when not is_numeric then true
        else raw_value::numeric < minimum_value
          or raw_value::numeric > maximum_value
      end
