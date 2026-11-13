with durable_airports as (
    select distinct airport_id
    from {{ ref('dim_airports') }}
),
airport_coverage as (
    select a.airport_id
    from durable_airports a
    left join {{ ref('ref_airport_timezones') }} t using (airport_id)
    group by a.airport_id
    having count(t.airport_id) <> 1
),
unknown_timezones as (
    select t.airport_id
    from {{ ref('ref_airport_timezones') }} t
    left join pg_timezone_names p on p.name = t.iana_timezone
    where p.name is null
)
select airport_id, 'coverage_not_exactly_one' as failure_reason from airport_coverage
union all
select airport_id, 'invalid_postgresql_iana_timezone' from unknown_timezones

