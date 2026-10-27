select
    coalesce(staging.flight_record_key, fact.flight_record_key) as flight_record_key,
    case
        when staging.flight_record_key is null then 'missing_from_staging'
        when fact.flight_record_key is null then 'missing_from_fact'
    end as coverage_issue
from {{ ref('stg_bts_flights') }} as staging
full outer join {{ ref('fact_flights') }} as fact using (flight_record_key)
where staging.flight_record_key is null
   or fact.flight_record_key is null
