with aggregated as (
    select
        month_start_date,
        {{ kpi_additive_metrics() }}
    from {{ ref('int_flight_kpi_components') }}
    group by month_start_date
),
with_cause_total as (
    select *, {{ kpi_total_cause_delay_minutes() }} as total_cause_delay_minutes
    from aggregated
)

select
    to_char(month_start_date, 'YYYYMM')::integer as month_key,
    extract(year from month_start_date)::smallint as year,
    extract(month from month_start_date)::smallint as month_number,
    with_cause_total.*,
    {{ kpi_derived_metrics() }}
from with_cause_total
