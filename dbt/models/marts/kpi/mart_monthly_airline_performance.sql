with aggregated as (
    select
        month_start_date,
        airline_key,
        {{ kpi_additive_metrics() }}
    from {{ ref('int_flight_kpi_components') }}
    group by month_start_date, airline_key
),
with_cause_total as (
    select *, {{ kpi_total_cause_delay_minutes() }} as total_cause_delay_minutes
    from aggregated
)

select
    {{ generate_key(['month_start_date', 'with_cause_total.airline_key']) }} as airline_month_key,
    to_char(month_start_date, 'YYYYMM')::integer as month_key,
    extract(year from month_start_date)::smallint as year,
    extract(month from month_start_date)::smallint as month_number,
    with_cause_total.*,
    airline.dot_airline_id,
    airline.reporting_airline_code,
    airline.iata_airline_code,
    {{ kpi_derived_metrics() }}
from with_cause_total
join {{ ref('dim_airlines') }} airline using (airline_key)
