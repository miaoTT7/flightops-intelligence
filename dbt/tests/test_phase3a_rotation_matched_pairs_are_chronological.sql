select previous_flight_record_key
from {{ ref('int_aircraft_rotation_pairing') }}
where rotation_match_status = 'matched'
  and (next_scheduled_departure_utc <= previous_scheduled_arrival_utc
       or scheduled_turnaround_minutes not between 20 and 360
       or next_actual_departure_utc < previous_actual_arrival_utc
       or actual_ground_minutes < 0)

