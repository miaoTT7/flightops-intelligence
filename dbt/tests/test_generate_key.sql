with generated as (
    select
        {{ generate_key(["'AA'", "'123'"]) }} as key_one,
        {{ generate_key(["'AA'", "'123'"]) }} as key_one_repeat,
        {{ generate_key(["'A'", "'A123'"]) }} as different_boundary_key,
        {{ generate_key(["'123'", "'AA'"]) }} as different_order_key,
        {{ generate_key(["cast(null as text)", "''"]) }} as null_empty_key,
        {{ generate_key(["''", "cast(null as text)"]) }} as empty_null_key
)
select *
from generated
where key_one is distinct from key_one_repeat
   or key_one = different_boundary_key
   or key_one = different_order_key
   or null_empty_key = empty_null_key
   or length(key_one) <> 32
   or key_one !~ '^[0-9a-f]{32}$'
