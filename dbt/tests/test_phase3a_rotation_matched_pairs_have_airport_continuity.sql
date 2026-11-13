select previous_flight_record_key
from {{ ref('int_aircraft_rotation_pairing') }}
where rotation_match_status = 'matched'
  and (connection_airport_id is distinct from next_origin_airport_id
       or connection_airport_code is distinct from next_origin_airport_code)

