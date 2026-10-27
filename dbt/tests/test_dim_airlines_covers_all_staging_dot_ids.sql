select distinct staging.dot_airline_id
from {{ ref('stg_bts_flights') }} as staging
left join {{ ref('dim_airlines') }} as airlines
    on staging.dot_airline_id = airlines.dot_airline_id
where staging.dot_airline_id is not null
  and airlines.dot_airline_id is null
