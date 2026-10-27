select
    airline_key,
    dot_airline_id
from {{ ref('dim_airlines') }}
where airline_key is distinct from {{ generate_key(['dot_airline_id']) }}
