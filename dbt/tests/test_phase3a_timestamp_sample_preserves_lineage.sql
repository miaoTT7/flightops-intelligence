select s.flight_record_key
from {{ ref('int_flight_timestamps_sample') }} s
left join {{ ref('fact_flights') }} f using (flight_record_key)
where f.flight_record_key is null
   or s.source_file_id <> f.source_file_id
   or s.source_row_number <> f.source_row_number

