{% set components = [
    'reported_flights',
    'official_arrival_ontime_flights',
    'arrival_observed_flights',
    'departure_delayed_15_flights',
    'departure_observed_flights',
    'arrival_delay_signed_minutes_sum',
    'arrival_delay_observation_count',
    'departure_delay_signed_minutes_sum',
    'departure_delay_observation_count',
    'cancelled_flights',
    'carrier_cancelled_flights',
    'weather_cancelled_flights',
    'nas_cancelled_flights',
    'security_cancelled_flights',
    'diverted_flights',
    'carrier_delay_minutes_sum',
    'weather_delay_minutes_sum',
    'nas_delay_minutes_sum',
    'security_delay_minutes_sum',
    'late_aircraft_delay_minutes_sum',
    'cause_reported_flights',
    'invalid_scheduled_elapsed_count',
    'invalid_actual_elapsed_count',
    'invalid_diversion_elapsed_count'
] %}

with fact_monthly as (
    select month_start_date, {{ kpi_additive_metrics() }}
    from {{ ref('int_flight_kpi_components') }}
    group by month_start_date
),
mart_monthly as (
    select month_start_date, {{ components | join(', ') }}
    from {{ ref('mart_monthly_overall_performance') }}
),
differences as (
    select * from fact_monthly
    except all
    select * from mart_monthly

    union all

    select * from mart_monthly
    except all
    select * from fact_monthly
)
select * from differences
