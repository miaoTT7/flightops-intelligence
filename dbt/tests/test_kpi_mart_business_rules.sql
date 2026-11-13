{% set marts = [
    ('mart_monthly_overall_performance', 'month_key'),
    ('mart_monthly_airline_performance', 'airline_month_key'),
    ('mart_monthly_origin_airport_performance', 'origin_airport_month_key'),
    ('mart_monthly_route_performance', 'route_month_key')
] %}

{% for model_name, grain_key in marts %}
select
    '{{ model_name }}'::text as model_name,
    {{ grain_key }}::text as grain_key
from {{ ref(model_name) }}
where reported_flights < 0
   or official_arrival_ontime_flights < 0
   or arrival_observed_flights < 0
   or departure_delayed_15_flights < 0
   or departure_observed_flights < 0
   or arrival_delay_observation_count < 0
   or departure_delay_observation_count < 0
   or cancelled_flights < 0
   or diverted_flights < 0
   or cause_reported_flights < 0
   or invalid_scheduled_elapsed_count < 0
   or invalid_actual_elapsed_count < 0
   or invalid_diversion_elapsed_count < 0
   or official_arrival_ontime_flights > arrival_observed_flights
   or official_arrival_ontime_flights > reported_flights
   or arrival_observed_flights > reported_flights
   or departure_delayed_15_flights > departure_observed_flights
   or departure_observed_flights > reported_flights
   or cancelled_flights > reported_flights
   or diverted_flights > reported_flights
   or carrier_cancelled_flights + weather_cancelled_flights
      + nas_cancelled_flights + security_cancelled_flights <> cancelled_flights
   or carrier_delay_minutes_sum < 0
   or weather_delay_minutes_sum < 0
   or nas_delay_minutes_sum < 0
   or security_delay_minutes_sum < 0
   or late_aircraft_delay_minutes_sum < 0
   or official_arrival_ontime_rate is distinct from
      official_arrival_ontime_flights::numeric / nullif(reported_flights, 0)
   or observed_arrival_ontime_rate is distinct from
      official_arrival_ontime_flights::numeric / nullif(arrival_observed_flights, 0)
   or departure_delayed_15_rate is distinct from
      departure_delayed_15_flights::numeric / nullif(departure_observed_flights, 0)
   or average_arrival_delay_minutes_signed is distinct from
      arrival_delay_signed_minutes_sum::numeric / nullif(arrival_delay_observation_count, 0)
   or average_departure_delay_minutes_signed is distinct from
      departure_delay_signed_minutes_sum::numeric / nullif(departure_delay_observation_count, 0)
   or cancellation_rate is distinct from cancelled_flights::numeric / nullif(reported_flights, 0)
   or diversion_rate is distinct from diverted_flights::numeric / nullif(reported_flights, 0)
   or official_arrival_ontime_rate not between 0 and 1
   or observed_arrival_ontime_rate not between 0 and 1
   or departure_delayed_15_rate not between 0 and 1
   or cancellation_rate not between 0 and 1
   or diversion_rate not between 0 and 1
   or carrier_delay_minutes_share not between 0 and 1
   or weather_delay_minutes_share not between 0 and 1
   or nas_delay_minutes_share not between 0 and 1
   or security_delay_minutes_share not between 0 and 1
   or late_aircraft_delay_minutes_share not between 0 and 1
   or (total_cause_delay_minutes is null and (
          carrier_delay_minutes_share is not null
       or weather_delay_minutes_share is not null
       or nas_delay_minutes_share is not null
       or security_delay_minutes_share is not null
       or late_aircraft_delay_minutes_share is not null
   ))
   or (total_cause_delay_minutes = 0 and (
          carrier_delay_minutes_share is not null
       or weather_delay_minutes_share is not null
       or nas_delay_minutes_share is not null
       or security_delay_minutes_share is not null
       or late_aircraft_delay_minutes_share is not null
   ))
   or (total_cause_delay_minutes > 0 and abs(
          carrier_delay_minutes_share + weather_delay_minutes_share
        + nas_delay_minutes_share + security_delay_minutes_share
        + late_aircraft_delay_minutes_share - 1
   ) > 0.000000000001)
   or (total_cause_delay_minutes > 0 and (
          carrier_delay_minutes_share is null
       or weather_delay_minutes_share is null
       or nas_delay_minutes_share is null
       or security_delay_minutes_share is null
       or late_aircraft_delay_minutes_share is null
   ))
{% if not loop.last %}union all{% endif %}
{% endfor %}
