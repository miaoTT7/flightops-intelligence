with airport_occurrences as (
    select
        origin_airport_sequence_id as airport_sequence_id,
        origin_airport_id as airport_id,
        origin_airport_code as airport_code,
        origin_city_market_id as city_market_id,
        origin_city_name as city_name,
        origin_state_code as state_code,
        origin_state_fips as state_fips,
        origin_state_name as state_name,
        origin_world_area_code as world_area_code
    from {{ ref('stg_bts_flights') }}

    union all

    select
        destination_airport_sequence_id as airport_sequence_id,
        destination_airport_id as airport_id,
        destination_airport_code as airport_code,
        destination_city_market_id as city_market_id,
        destination_city_name as city_name,
        destination_state_code as state_code,
        destination_state_fips as state_fips,
        destination_state_name as state_name,
        destination_world_area_code as world_area_code
    from {{ ref('stg_bts_flights') }}
),

distinct_airport_attributes as (
    select distinct
        airport_sequence_id,
        airport_id,
        airport_code,
        city_market_id,
        city_name,
        state_code,
        state_fips,
        state_name,
        world_area_code
    from airport_occurrences
)

select
    {{ generate_key(['airport_sequence_id']) }} as airport_key,
    airport_sequence_id,
    airport_id,
    airport_code,
    city_market_id,
    city_name,
    state_code,
    state_fips,
    state_name,
    world_area_code
from distinct_airport_attributes
