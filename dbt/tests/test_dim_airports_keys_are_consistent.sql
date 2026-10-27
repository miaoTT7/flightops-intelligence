select
    airport_key,
    airport_sequence_id
from {{ ref('dim_airports') }}
where airport_key is distinct from {{ generate_key(['airport_sequence_id']) }}
