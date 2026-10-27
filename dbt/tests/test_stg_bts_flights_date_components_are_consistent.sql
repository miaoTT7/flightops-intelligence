select
    flight_record_key,
    flight_date,
    flight_year,
    flight_quarter,
    flight_month,
    day_of_month,
    day_of_week
from {{ ref('stg_bts_flights') }}
where flight_year is distinct from extract(year from flight_date)::smallint
   or flight_quarter is distinct from extract(quarter from flight_date)::smallint
   or flight_month is distinct from extract(month from flight_date)::smallint
   or day_of_month is distinct from extract(day from flight_date)::smallint
   or day_of_week is distinct from extract(isodow from flight_date)::smallint
