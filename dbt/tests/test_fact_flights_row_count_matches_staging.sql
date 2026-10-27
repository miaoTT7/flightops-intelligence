select
    (select count(*) from {{ ref('stg_bts_flights') }}) as staging_rows,
    (select count(*) from {{ ref('fact_flights') }}) as fact_rows
where (select count(*) from {{ ref('stg_bts_flights') }})
    <> (select count(*) from {{ ref('fact_flights') }})
