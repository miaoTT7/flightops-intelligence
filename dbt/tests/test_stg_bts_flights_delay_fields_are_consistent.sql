select flight_record_key, 'departure' as delay_type
from {{ ref('stg_bts_flights') }}
where departure_delay_minutes is distinct from
      case
          when departure_delay_minutes_signed is null then null
          else greatest(departure_delay_minutes_signed, 0)
      end
   or is_departure_delayed_15_minutes is distinct from
      case
          when departure_delay_minutes_signed is null then null
          else departure_delay_minutes_signed >= 15
      end

union all

select flight_record_key, 'arrival' as delay_type
from {{ ref('stg_bts_flights') }}
where arrival_delay_minutes is distinct from
      case
          when arrival_delay_minutes_signed is null then null
          else greatest(arrival_delay_minutes_signed, 0)
      end
   or is_arrival_delayed_15_minutes is distinct from
      case
          when arrival_delay_minutes_signed is null then null
          else arrival_delay_minutes_signed >= 15
      end
