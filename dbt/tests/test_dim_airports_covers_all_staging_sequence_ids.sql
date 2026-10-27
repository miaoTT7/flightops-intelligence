with staging_airports as (
    select distinct
        'origin'::text as airport_role,
        origin_airport_sequence_id as airport_sequence_id
    from {{ ref('stg_bts_flights') }}

    union

    select distinct
        'destination'::text as airport_role,
        destination_airport_sequence_id as airport_sequence_id
    from {{ ref('stg_bts_flights') }}
)

select
    staging_airports.airport_role,
    staging_airports.airport_sequence_id
from staging_airports
left join {{ ref('dim_airports') }} as airports using (airport_sequence_id)
where staging_airports.airport_sequence_id is not null
  and airports.airport_sequence_id is null
