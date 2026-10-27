select
    flight_record_key
from {{ ref('fact_flights') }}
where flight_date_key is distinct from to_char(flight_date, 'YYYYMMDD')::integer
   or airline_key is distinct from {{ generate_key(['dot_airline_id']) }}
   or origin_airport_key is distinct from {{ generate_key(['origin_airport_sequence_id']) }}
   or destination_airport_key is distinct from {{ generate_key(['destination_airport_sequence_id']) }}
