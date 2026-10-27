select
    flight_record_key,
    is_diverted,
    arrival_delay_minutes_signed,
    arrival_delay_minutes,
    is_arrival_delayed_15_minutes,
    arrival_delay_group,
    diversion_arrival_delay_minutes
from {{ ref('stg_bts_flights') }}
where (
        is_diverted
        and (
            arrival_delay_minutes_signed is not null
            or arrival_delay_minutes is not null
            or is_arrival_delayed_15_minutes is not null
            or arrival_delay_group is not null
        )
    )
   or (not is_diverted and diversion_arrival_delay_minutes is not null)
