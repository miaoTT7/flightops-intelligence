select
    dot_airline_id,
    count(distinct iata_airline_code) filter (
        where iata_airline_code is not null
    ) as non_null_iata_airline_code_count
from {{ ref('stg_bts_flights') }}
group by dot_airline_id
having count(distinct iata_airline_code) filter (
    where iata_airline_code is not null
) > 1
