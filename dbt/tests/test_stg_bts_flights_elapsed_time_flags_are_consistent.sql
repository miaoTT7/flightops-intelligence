select flight_record_key
from {{ ref('stg_bts_flights') }}
where is_scheduled_elapsed_time_valid is distinct from
          case when scheduled_elapsed_minutes is null then null else scheduled_elapsed_minutes >= 0 end
   or is_actual_elapsed_time_valid is distinct from
          case when actual_elapsed_minutes is null then null else actual_elapsed_minutes >= 0 end
   or is_diversion_actual_elapsed_time_valid is distinct from
          case when diversion_actual_elapsed_minutes is null then null else diversion_actual_elapsed_minutes >= 0 end
