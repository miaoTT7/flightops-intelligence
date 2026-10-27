with staging_values as (
    select
        flight_record_key, source_file_id, source_row_number, batch_id, ingested_at,
        flight_date, dot_airline_id, reporting_airline_code, iata_airline_code,
        flight_number, tail_number,
        origin_airport_id, origin_airport_sequence_id, origin_airport_code,
        destination_airport_id, destination_airport_sequence_id, destination_airport_code,
        scheduled_departure_time, scheduled_departure_day_offset,
        actual_departure_time, actual_departure_day_offset,
        departure_delay_minutes_signed, departure_delay_minutes,
        is_departure_delayed_15_minutes, departure_delay_group, departure_time_block,
        taxi_out_minutes, wheels_off_time, wheels_off_day_offset,
        wheels_on_time, wheels_on_day_offset, taxi_in_minutes,
        scheduled_arrival_time, scheduled_arrival_day_offset,
        actual_arrival_time, actual_arrival_day_offset,
        arrival_delay_minutes_signed, arrival_delay_minutes,
        is_arrival_delayed_15_minutes, arrival_delay_group, arrival_time_block,
        is_cancelled, cancellation_code, is_diverted,
        scheduled_elapsed_minutes, actual_elapsed_minutes, air_time_minutes,
        flight_count, distance_miles, distance_group,
        carrier_delay_minutes, weather_delay_minutes, nas_delay_minutes,
        security_delay_minutes, late_aircraft_delay_minutes,
        first_departure_time, first_departure_day_offset,
        total_added_ground_time_minutes, longest_added_ground_time_minutes,
        diverted_airport_landings, diversion_reached_destination,
        diversion_actual_elapsed_minutes, diversion_arrival_delay_minutes,
        diversion_distance_miles
    from {{ ref('stg_bts_flights') }}
),
fact_values as (
    select
        flight_record_key, source_file_id, source_row_number, batch_id, ingested_at,
        flight_date, dot_airline_id, reporting_airline_code, iata_airline_code,
        flight_number, tail_number,
        origin_airport_id, origin_airport_sequence_id, origin_airport_code,
        destination_airport_id, destination_airport_sequence_id, destination_airport_code,
        scheduled_departure_time, scheduled_departure_day_offset,
        actual_departure_time, actual_departure_day_offset,
        departure_delay_minutes_signed, departure_delay_minutes,
        is_departure_delayed_15_minutes, departure_delay_group, departure_time_block,
        taxi_out_minutes, wheels_off_time, wheels_off_day_offset,
        wheels_on_time, wheels_on_day_offset, taxi_in_minutes,
        scheduled_arrival_time, scheduled_arrival_day_offset,
        actual_arrival_time, actual_arrival_day_offset,
        arrival_delay_minutes_signed, arrival_delay_minutes,
        is_arrival_delayed_15_minutes, arrival_delay_group, arrival_time_block,
        is_cancelled, cancellation_code, is_diverted,
        scheduled_elapsed_minutes, actual_elapsed_minutes, air_time_minutes,
        flight_count, distance_miles, distance_group,
        carrier_delay_minutes, weather_delay_minutes, nas_delay_minutes,
        security_delay_minutes, late_aircraft_delay_minutes,
        first_departure_time, first_departure_day_offset,
        total_added_ground_time_minutes, longest_added_ground_time_minutes,
        diverted_airport_landings, diversion_reached_destination,
        diversion_actual_elapsed_minutes, diversion_arrival_delay_minutes,
        diversion_distance_miles
    from {{ ref('fact_flights') }}
),
missing_or_changed_in_fact as (
    select * from staging_values
    except all
    select * from fact_values
),
unexpected_or_changed_in_fact as (
    select * from fact_values
    except all
    select * from staging_values
)

select 'missing_or_changed_in_fact'::text as difference_type, *
from missing_or_changed_in_fact
union all
select 'unexpected_or_changed_in_fact'::text as difference_type, *
from unexpected_or_changed_in_fact
