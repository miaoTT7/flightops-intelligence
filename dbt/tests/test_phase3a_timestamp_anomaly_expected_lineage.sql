with expected(source_row_number, scheduled_issue, actual_issue) as (
    values
        (437917::bigint,true,false),(528504::bigint,false,true),
        (4060::bigint,false,true),(31576::bigint,false,true),
        (441439::bigint,true,true),(190339::bigint,true,false),
        (402742::bigint,true,false),(425072::bigint,true,true),
        (539454::bigint,true,false),(402752::bigint,true,false),
        (456597::bigint,true,true),(480160::bigint,false,true),
        (459245::bigint,false,true)
), expected_stable as (
    select 'd7c7d59452cad1215d9605e8ff350a4bad7282750765084fe57928a5ad275453' as csv_sha256,
           source_row_number, scheduled_issue, actual_issue
    from expected
), actual as (
    select csv_sha256, source_row_number,
           has_scheduled_elapsed_inconsistency as scheduled_issue,
           has_actual_arrival_validation_mismatch as actual_issue
    from {{ ref('audit_flight_timestamp_anomalies') }}
    where source_year = 2025 and source_month = 1
), differences as (
    (select * from expected_stable except select * from actual)
    union all (select * from actual except select * from expected_stable)
)
select * from differences
