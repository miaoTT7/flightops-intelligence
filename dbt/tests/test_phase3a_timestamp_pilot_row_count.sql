with input_count as (
    select count(*) as row_count
    from {{ ref('fact_flights') }}
    where flight_date >= '{{ var("phase3a_batch_start_date") }}'::date
      and flight_date < '{{ var("phase3a_batch_end_date") }}'::date
),
output_count as (
    select count(*) as row_count
    from {{ ref('int_flight_timestamps') }}
    where flight_date >= '{{ var("phase3a_batch_start_date") }}'::date
      and flight_date < '{{ var("phase3a_batch_end_date") }}'::date
)
select input_count.row_count as input_rows,
       output_count.row_count as output_rows
from input_count cross join output_count
where input_count.row_count <> output_count.row_count
