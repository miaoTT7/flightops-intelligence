with expected_exceptions(
    source_year,
    source_month,
    csv_sha256,
    source_row_number,
    raw_flight_number
) as (
    values (
        2024,
        8,
        'a154c46b18d8dad0be6bbc30d9d01c840de697650b909e563475fc3a8d622d44'::text,
        234964::bigint,
        ''::text
    )
),
actual_exceptions as (
    select
        sf.source_year,
        sf.source_month,
        sf.csv_sha256,
        stg.source_row_number,
        raw.flight_number_reporting_airline as raw_flight_number
    from {{ ref('stg_bts_flights') }} stg
    join {{ source('bts_raw', 'bts_on_time_performance') }} raw
        using (source_file_id, source_row_number)
    join {{ source('ingestion_metadata', 'source_file') }} sf
        using (source_file_id)
    where stg.flight_number is null
),
missing_or_changed as (
    select * from expected_exceptions
    except all
    select * from actual_exceptions
),
unexpected as (
    select * from actual_exceptions
    except all
    select * from expected_exceptions
)
select 'missing_or_changed'::text as difference_type, *
from missing_or_changed
union all
select 'unexpected'::text as difference_type, *
from unexpected
