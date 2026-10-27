with origins as (
    select distinct
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
),
destinations as (
    select distinct
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
)

select
    origins.airport_sequence_id
from origins
inner join destinations using (airport_sequence_id)
where row(
    origins.airport_id,
    origins.airport_code,
    origins.city_market_id,
    origins.city_name,
    origins.state_code,
    origins.state_fips,
    origins.state_name,
    origins.world_area_code
) is distinct from row(
    destinations.airport_id,
    destinations.airport_code,
    destinations.city_market_id,
    destinations.city_name,
    destinations.state_code,
    destinations.state_fips,
    destinations.state_name,
    destinations.world_area_code
)
