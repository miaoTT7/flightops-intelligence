select
    airport_sequence_id,
    state_fips
from {{ ref('dim_airports') }}
where state_fips is not null
  and state_fips !~ '^[0-9]{2}$'
