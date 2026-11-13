with expected(category) as (
    values
        ('cross_timezone'), ('overnight_clock'), ('dst_spring'), ('dst_fall'),
        ('cancelled'), ('diverted'), ('raw_2400')
),
actual as (
    select distinct sample_category as category
    from {{ ref('int_flight_timestamps_sample') }}
)
select expected.category
from expected
left join actual using (category)
where actual.category is null
