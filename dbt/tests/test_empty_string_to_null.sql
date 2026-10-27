with test_cases(input_value, expected_value) as (
    values
        (cast(null as text), cast(null as text)),
        ('',                    cast(null as text)),
        ('   ',                 cast(null as text)),
        ('  AA  ',              'AA'),
        ('0',                   '0')
),
evaluated as (
    select
        input_value,
        expected_value,
        {{ empty_string_to_null('input_value') }} as actual_value
    from test_cases
)
select *
from evaluated
where actual_value is distinct from expected_value
