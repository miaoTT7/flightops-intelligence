with expected_dates as (
    select calendar_timestamp::date as date_day
    from generate_series(
        date '2024-01-01',
        date '2025-12-31',
        interval '1 day'
    ) as generated_dates(calendar_timestamp)
),
actual_dates as (
    select date_day
    from {{ ref('dim_dates') }}
),
date_differences as (
    select
        coalesce(expected_dates.date_day, actual_dates.date_day) as date_day,
        case
            when expected_dates.date_day is null then 'unexpected'
            when actual_dates.date_day is null then 'missing'
        end as difference_type
    from expected_dates
    full outer join actual_dates using (date_day)
    where expected_dates.date_day is null
       or actual_dates.date_day is null
),
invalid_summary as (
    select null::date as date_day, 'invalid_summary'::text as difference_type
    from actual_dates
    having count(*) <> 731
        or count(distinct date_day) <> 731
        or min(date_day) <> date '2024-01-01'
        or max(date_day) <> date '2025-12-31'
)

select * from date_differences
union all
select * from invalid_summary
