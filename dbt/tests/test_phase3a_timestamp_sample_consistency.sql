select flight_record_key
from {{ ref('int_flight_timestamps_sample') }}
where (scheduled_departure_status = 'resolved_unique')
          <> (scheduled_departure_utc is not null)
   or (scheduled_arrival_status = 'resolved_unique')
          <> (scheduled_arrival_utc is not null)
   or scheduled_departure_candidate_count not between 0 and 2
   or scheduled_arrival_candidate_count < 0
   or (actual_departure_status = 'validated' and actual_departure_utc is null)
   or (actual_arrival_status = 'validated' and actual_arrival_utc is null)
   or (sample_category = 'raw_2400'
       and scheduled_departure_day_offset <> 1
       and scheduled_arrival_day_offset <> 1)

