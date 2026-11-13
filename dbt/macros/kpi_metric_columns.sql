{% macro kpi_additive_metrics() -%}
    sum(reported_flight_count)::bigint as reported_flights,
    sum(official_arrival_ontime_flight_count)::bigint as official_arrival_ontime_flights,
    sum(arrival_observed_flight_count)::bigint as arrival_observed_flights,
    sum(departure_delayed_15_flight_count)::bigint as departure_delayed_15_flights,
    sum(departure_observed_flight_count)::bigint as departure_observed_flights,
    sum(arrival_delay_signed_minutes_value)::bigint as arrival_delay_signed_minutes_sum,
    sum(arrival_delay_observation_count)::bigint as arrival_delay_observation_count,
    sum(departure_delay_signed_minutes_value)::bigint as departure_delay_signed_minutes_sum,
    sum(departure_delay_observation_count)::bigint as departure_delay_observation_count,
    sum(cancelled_flight_count)::bigint as cancelled_flights,
    sum(carrier_cancelled_flight_count)::bigint as carrier_cancelled_flights,
    sum(weather_cancelled_flight_count)::bigint as weather_cancelled_flights,
    sum(nas_cancelled_flight_count)::bigint as nas_cancelled_flights,
    sum(security_cancelled_flight_count)::bigint as security_cancelled_flights,
    sum(diverted_flight_count)::bigint as diverted_flights,
    sum(carrier_delay_minutes)::bigint as carrier_delay_minutes_sum,
    sum(weather_delay_minutes)::bigint as weather_delay_minutes_sum,
    sum(nas_delay_minutes)::bigint as nas_delay_minutes_sum,
    sum(security_delay_minutes)::bigint as security_delay_minutes_sum,
    sum(late_aircraft_delay_minutes)::bigint as late_aircraft_delay_minutes_sum,
    sum(cause_reported_flight_count)::bigint as cause_reported_flights,
    sum(invalid_scheduled_elapsed_count)::bigint as invalid_scheduled_elapsed_count,
    sum(invalid_actual_elapsed_count)::bigint as invalid_actual_elapsed_count,
    sum(invalid_diversion_elapsed_count)::bigint as invalid_diversion_elapsed_count
{%- endmacro %}

{% macro kpi_total_cause_delay_minutes() -%}
    case
        when carrier_delay_minutes_sum is not null
          or weather_delay_minutes_sum is not null
          or nas_delay_minutes_sum is not null
          or security_delay_minutes_sum is not null
          or late_aircraft_delay_minutes_sum is not null
        then coalesce(carrier_delay_minutes_sum, 0)
           + coalesce(weather_delay_minutes_sum, 0)
           + coalesce(nas_delay_minutes_sum, 0)
           + coalesce(security_delay_minutes_sum, 0)
           + coalesce(late_aircraft_delay_minutes_sum, 0)
    end
{%- endmacro %}

{% macro kpi_derived_metrics() -%}
    official_arrival_ontime_flights::numeric / nullif(reported_flights, 0)
        as official_arrival_ontime_rate,
    official_arrival_ontime_flights::numeric / nullif(arrival_observed_flights, 0)
        as observed_arrival_ontime_rate,
    departure_delayed_15_flights::numeric / nullif(departure_observed_flights, 0)
        as departure_delayed_15_rate,
    arrival_delay_signed_minutes_sum::numeric / nullif(arrival_delay_observation_count, 0)
        as average_arrival_delay_minutes_signed,
    departure_delay_signed_minutes_sum::numeric / nullif(departure_delay_observation_count, 0)
        as average_departure_delay_minutes_signed,
    cancelled_flights::numeric / nullif(reported_flights, 0) as cancellation_rate,
    diverted_flights::numeric / nullif(reported_flights, 0) as diversion_rate,
    carrier_delay_minutes_sum::numeric / nullif(total_cause_delay_minutes, 0)
        as carrier_delay_minutes_share,
    weather_delay_minutes_sum::numeric / nullif(total_cause_delay_minutes, 0)
        as weather_delay_minutes_share,
    nas_delay_minutes_sum::numeric / nullif(total_cause_delay_minutes, 0)
        as nas_delay_minutes_share,
    security_delay_minutes_sum::numeric / nullif(total_cause_delay_minutes, 0)
        as security_delay_minutes_share,
    late_aircraft_delay_minutes_sum::numeric / nullif(total_cause_delay_minutes, 0)
        as late_aircraft_delay_minutes_share
{%- endmacro %}
