with date_spine as (
    select calendar_timestamp::date as date_day
    from generate_series(
        date '2024-01-01',
        date '2025-12-31',
        interval '1 day'
    ) as generated_dates(calendar_timestamp)
)

select
    to_char(date_day, 'YYYYMMDD')::integer as date_key,
    date_day,
    extract(year from date_day)::smallint as year,
    extract(quarter from date_day)::smallint as quarter,
    extract(month from date_day)::smallint as month_number,
    case extract(month from date_day)::smallint
        when 1 then 'January'
        when 2 then 'February'
        when 3 then 'March'
        when 4 then 'April'
        when 5 then 'May'
        when 6 then 'June'
        when 7 then 'July'
        when 8 then 'August'
        when 9 then 'September'
        when 10 then 'October'
        when 11 then 'November'
        when 12 then 'December'
    end::text as month_name,
    extract(day from date_day)::smallint as day_of_month,
    extract(isodow from date_day)::smallint as day_of_week_number,
    case extract(isodow from date_day)::smallint
        when 1 then 'Monday'
        when 2 then 'Tuesday'
        when 3 then 'Wednesday'
        when 4 then 'Thursday'
        when 5 then 'Friday'
        when 6 then 'Saturday'
        when 7 then 'Sunday'
    end::text as day_of_week_name,
    extract(isodow from date_day)::smallint in (6, 7) as is_weekend
from date_spine
