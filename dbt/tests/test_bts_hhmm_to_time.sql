with test_cases(input_value, expected_time, expected_day_offset) as (
    values
        (cast(null as text), cast(null as time), cast(null as integer)),
        ('',                    cast(null as time), cast(null as integer)),
        ('   ',                 cast(null as time), cast(null as integer)),
        ('0',                   time '00:00:00', 0),
        ('5',                   time '00:05:00', 0),
        ('30',                  time '00:30:00', 0),
        ('700',                 time '07:00:00', 0),
        ('1234',                time '12:34:00', 0),
        ('2359',                time '23:59:00', 0),
        ('2400',                time '00:00:00', 1),
        ('2360',                cast(null as time), cast(null as integer)),
        ('2401',                cast(null as time), cast(null as integer)),
        ('-100',                cast(null as time), cast(null as integer)),
        ('12:30',               cast(null as time), cast(null as integer)),
        ('abcd',                cast(null as time), cast(null as integer))
),
evaluated as (
    select
        input_value,
        expected_time,
        expected_day_offset,
        {{ bts_hhmm_to_time('input_value') }} as actual_time,
        {{ bts_hhmm_to_time('input_value', part='day_offset') }} as actual_day_offset
    from test_cases
)
select *
from evaluated
where actual_time is distinct from expected_time
   or actual_day_offset is distinct from expected_day_offset
