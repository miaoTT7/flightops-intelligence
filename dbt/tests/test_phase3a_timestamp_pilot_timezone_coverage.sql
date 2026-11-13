select flight_record_key
from {{ ref('int_flight_timestamps') }}
where flight_date >= '{{ var("phase3a_batch_start_date") }}'::date
  and flight_date < '{{ var("phase3a_batch_end_date") }}'::date
  and (origin_iana_timezone is null or destination_iana_timezone is null)
