select flight_record_key, flight_count
from {{ ref('stg_bts_flights') }}
where flight_count is distinct from 1
