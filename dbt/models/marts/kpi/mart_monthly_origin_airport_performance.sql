with aggregated as (
    select
        month_start_date,
        origin_airport_key,
        {{ kpi_additive_metrics() }}
    from {{ ref('int_flight_kpi_components') }}
    group by month_start_date, origin_airport_key
),
with_cause_total as (
    select *, {{ kpi_total_cause_delay_minutes() }} as total_cause_delay_minutes
    from aggregated
)

select
    {{ generate_key(['month_start_date', 'with_cause_total.origin_airport_key']) }}
        as origin_airport_month_key,
    to_char(month_start_date, 'YYYYMM')::integer as month_key,
    extract(year from month_start_date)::smallint as year,
    extract(month from month_start_date)::smallint as month_number,
    with_cause_total.*,
    airport.airport_sequence_id as origin_airport_sequence_id,
    airport.airport_id as origin_airport_id,
    airport.airport_code as origin_airport_code,
    airport.city_name as origin_city_name,
    airport.state_code as origin_state_code,
    {{ kpi_derived_metrics() }}
from with_cause_total
join {{ ref('dim_airports') }} airport
    on airport.airport_key = with_cause_total.origin_airport_key
