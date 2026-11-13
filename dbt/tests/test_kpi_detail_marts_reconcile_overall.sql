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
{% set detail_marts = [
    'mart_monthly_airline_performance',
    'mart_monthly_origin_airport_performance',
    'mart_monthly_route_performance'
] %}

with overall as (
    select month_start_date, {{ components | join(', ') }}
    from {{ ref('mart_monthly_overall_performance') }}
),
detail_rollups as (
{% for model_name in detail_marts %}
    select
        '{{ model_name }}'::text as model_name,
        month_start_date,
        {% for column_name in components %}
        sum({{ column_name }}) as {{ column_name }}{% if not loop.last %},{% endif %}
        {% endfor %}
    from {{ ref(model_name) }}
    group by month_start_date
    {% if not loop.last %}union all{% endif %}
{% endfor %}
)
select detail_rollups.*
from detail_rollups
join overall using (month_start_date)
where
{% for column_name in components %}
    detail_rollups.{{ column_name }} is distinct from overall.{{ column_name }}
    {% if not loop.last %}or{% endif %}
{% endfor %}
