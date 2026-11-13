select flight_record_key
from {{ ref('int_flight_timestamps') }}
where flight_date >= '{{ var("phase3a_batch_start_date") }}'::date
  and flight_date < '{{ var("phase3a_batch_end_date") }}'::date
  and ((scheduled_departure_status = 'resolved_unique') <> (scheduled_departure_utc is not null)
   or (scheduled_arrival_status = 'resolved_unique') <> (scheduled_arrival_utc is not null)
   or scheduled_departure_candidate_count not between 0 and 2
   or scheduled_arrival_candidate_count < 0
   or (scheduled_arrival_status = 'resolved_unique'
       and abs(extract(epoch from (scheduled_arrival_utc - scheduled_departure_utc)) / 60.0
               - scheduled_elapsed_minutes) > 1)
   or (actual_departure_utc is not null
       and abs(extract(epoch from (actual_departure_utc - scheduled_departure_utc)) / 60.0
               - departure_delay_minutes_signed) > 0.001)
   or (actual_arrival_utc is not null
       and abs(extract(epoch from (actual_arrival_utc - actual_departure_utc)) / 60.0
               - actual_elapsed_minutes) > 0.001)
   or (actual_departure_status = 'validated'
       and ((actual_departure_utc is null)
            or (actual_departure_utc at time zone origin_iana_timezone)::time <> actual_departure_time))
   or (actual_arrival_status = 'validated'
       and ((actual_arrival_utc is null)
            or (actual_arrival_utc at time zone destination_iana_timezone)::time <> actual_arrival_time
            or (scheduled_arrival_utc is not null and arrival_delay_minutes_signed is not null
                and abs(extract(epoch from (actual_arrival_utc - scheduled_arrival_utc)) / 60.0
                        - arrival_delay_minutes_signed) > 1))))
