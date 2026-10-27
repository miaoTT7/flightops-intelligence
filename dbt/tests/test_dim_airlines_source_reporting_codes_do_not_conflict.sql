select
    dot_airline_id,
    count(distinct reporting_airline_code) as reporting_airline_code_count
from {{ ref('stg_bts_flights') }}
group by dot_airline_id
having count(distinct reporting_airline_code) <> 1
