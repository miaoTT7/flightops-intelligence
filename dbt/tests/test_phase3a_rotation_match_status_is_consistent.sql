select previous_flight_record_key
from {{ ref('int_aircraft_rotation_pairing') }}
where (rotation_match_status = 'matched') <> (rotation_exclusion_reason = 'matched')
   or (rotation_match_status = 'matched' and
       (tail_number is null
        or next_flight_record_key is null
        or previous_actual_arrival_utc is null
        or next_actual_departure_utc is null))

