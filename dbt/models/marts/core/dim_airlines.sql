with airline_attributes as (
    select distinct
        dot_airline_id,
        reporting_airline_code,
        iata_airline_code
    from {{ ref('stg_bts_flights') }}
)

select
    {{ generate_key(['dot_airline_id']) }} as airline_key,
    dot_airline_id,
    reporting_airline_code,
    iata_airline_code
from airline_attributes
