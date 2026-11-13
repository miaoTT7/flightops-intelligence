with expected_exceptions(source_year, source_month, csv_sha256, source_row_number, field_name, raw_value) as (
    values
        (2024, 3,  '921fb78d9f7e4e181ecee146dbd6dc7925ccbae53fbdc0677e1c69e820be94c1', 540698::bigint, 'crs_elapsed_time', '-160.00'),
        (2025, 1,  'd7c7d59452cad1215d9605e8ff350a4bad7282750765084fe57928a5ad275453', 81598::bigint,  'div_actual_elapsed_time', '-175.00'),
        (2025, 11, '6d6d63f3bb312a6695d4a8b17958bc47e4e71fdf7396ec882c9c9a61faa6efc2', 52880::bigint,  'crs_elapsed_time', '-60.00'),
        (2025, 11, '6d6d63f3bb312a6695d4a8b17958bc47e4e71fdf7396ec882c9c9a61faa6efc2', 491825::bigint, 'crs_elapsed_time', '-85.00'),
        (2025, 11, '6d6d63f3bb312a6695d4a8b17958bc47e4e71fdf7396ec882c9c9a61faa6efc2', 534601::bigint, 'crs_elapsed_time', '-99.00'),
        (2025, 11, '6d6d63f3bb312a6695d4a8b17958bc47e4e71fdf7396ec882c9c9a61faa6efc2', 534605::bigint, 'crs_elapsed_time', '-67.00'),
        (2025, 12, 'ed0a645562652fe2d816fbcb13ba46df6e3306344d9c4728c7ce5fe57bbd0db5', 173971::bigint, 'crs_elapsed_time', '-61.00')
),
actual_exceptions as (
    select
        sf.source_year,
        sf.source_month,
        sf.csv_sha256,
        r.source_row_number,
        values_to_check.field_name,
        btrim(values_to_check.raw_value) as raw_value
    from {{ source('bts_raw', 'bts_on_time_performance') }} r
    join {{ source('ingestion_metadata', 'source_file') }} sf using (source_file_id)
    cross join lateral (
        values
            ('crs_elapsed_time', r.crs_elapsed_time),
            ('actual_elapsed_time', r.actual_elapsed_time),
            ('div_actual_elapsed_time', r.div_actual_elapsed_time)
    ) as values_to_check(field_name, raw_value)
    where nullif(btrim(values_to_check.raw_value), '') is not null
      and pg_input_is_valid(btrim(values_to_check.raw_value), 'numeric')
      and btrim(values_to_check.raw_value)::numeric < 0
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
select 'missing_or_changed'::text as difference_type, * from missing_or_changed
union all
select 'unexpected'::text as difference_type, * from unexpected
