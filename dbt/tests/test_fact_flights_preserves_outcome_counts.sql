with staging_counts as (
    select
        count(*) filter (where is_cancelled) as cancelled_count,
        count(*) filter (where is_diverted) as diverted_count
    from {{ ref('stg_bts_flights') }}
),
fact_counts as (
    select
        count(*) filter (where is_cancelled) as cancelled_count,
        count(*) filter (where is_diverted) as diverted_count
    from {{ ref('fact_flights') }}
)

select staging_counts.*, fact_counts.*
from staging_counts
cross join fact_counts
where staging_counts.cancelled_count <> fact_counts.cancelled_count
   or staging_counts.diverted_count <> fact_counts.diverted_count
