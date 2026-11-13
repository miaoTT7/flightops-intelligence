select next_flight_record_key
from {{ ref('int_aircraft_rotation_pairing') }}
where rotation_match_status = 'matched'
group by next_flight_record_key
having count(*) > 1

