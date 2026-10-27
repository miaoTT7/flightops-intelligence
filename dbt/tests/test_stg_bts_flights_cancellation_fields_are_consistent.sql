select flight_record_key, is_cancelled, cancellation_code
from {{ ref('stg_bts_flights') }}
where (is_cancelled and cancellation_code is null)
   or (not is_cancelled and cancellation_code is not null)
