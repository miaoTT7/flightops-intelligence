select
    date_key,
    date_day
from {{ ref('dim_dates') }}
where date_key is distinct from to_char(date_day, 'YYYYMMDD')::integer
   or year is distinct from extract(year from date_day)::smallint
   or quarter is distinct from extract(quarter from date_day)::smallint
   or month_number is distinct from extract(month from date_day)::smallint
   or month_name is distinct from case extract(month from date_day)::smallint
        when 1 then 'January'
        when 2 then 'February'
        when 3 then 'March'
        when 4 then 'April'
        when 5 then 'May'
        when 6 then 'June'
        when 7 then 'July'
        when 8 then 'August'
        when 9 then 'September'
        when 10 then 'October'
        when 11 then 'November'
        when 12 then 'December'
    end
   or day_of_month is distinct from extract(day from date_day)::smallint
   or day_of_week_number is distinct from extract(isodow from date_day)::smallint
   or day_of_week_name is distinct from case extract(isodow from date_day)::smallint
        when 1 then 'Monday'
        when 2 then 'Tuesday'
        when 3 then 'Wednesday'
        when 4 then 'Thursday'
        when 5 then 'Friday'
        when 6 then 'Saturday'
        when 7 then 'Sunday'
    end
   or is_weekend is distinct from (extract(isodow from date_day)::smallint in (6, 7))
