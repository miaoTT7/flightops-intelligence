select p.flight_record_key
from {{ ref('int_flight_timestamps') }} p
left join {{ ref('fact_flights') }} f using (flight_record_key)
where p.flight_date >= '{{ var("phase3a_batch_start_date") }}'::date
  and p.flight_date < '{{ var("phase3a_batch_end_date") }}'::date
  and (f.flight_record_key is null
       or p.source_file_id <> f.source_file_id
       or p.source_row_number <> f.source_row_number
       or p.batch_id <> f.batch_id)
