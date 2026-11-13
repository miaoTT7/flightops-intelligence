with expected(stable_source_record_key) as (
    select value
    from (values
        ('8698d29045044a70986640a22a9b43e69c45eae5a6f3f8e9b70db9db3dca1c58:135665'),
        ('8698d29045044a70986640a22a9b43e69c45eae5a6f3f8e9b70db9db3dca1c58:140016'),
        ('8698d29045044a70986640a22a9b43e69c45eae5a6f3f8e9b70db9db3dca1c58:154878'),
        ('8698d29045044a70986640a22a9b43e69c45eae5a6f3f8e9b70db9db3dca1c58:332177'),
        ('8698d29045044a70986640a22a9b43e69c45eae5a6f3f8e9b70db9db3dca1c58:384908'),
        ('8698d29045044a70986640a22a9b43e69c45eae5a6f3f8e9b70db9db3dca1c58:496832')
    ) keys(value)
    where '{{ var("phase3a_batch_start_date") }}'::date <= date '2024-11-03'
      and '{{ var("phase3a_batch_end_date") }}'::date > date '2024-11-03'
), known_actual as (
    select sf.csv_sha256::text || ':' || t.source_row_number::text as stable_source_record_key
    from {{ ref('int_flight_timestamps') }} t
    join {{ source('ingestion_metadata', 'source_file') }} sf using (source_file_id)
    where t.flight_date >= '{{ var("phase3a_batch_start_date") }}'::date
      and t.flight_date < '{{ var("phase3a_batch_end_date") }}'::date
      and sf.csv_sha256::text || ':' || t.source_row_number::text
          in (select stable_source_record_key from expected)
      and t.scheduled_departure_candidate_count = 2
      and t.scheduled_departure_status = 'ambiguous_local_time'
      and t.scheduled_departure_utc is null
      and t.scheduled_arrival_status = 'unresolved_ambiguous_departure'
      and t.scheduled_arrival_utc is null
), set_difference as (
    (select * from expected except select * from known_actual)
    union all
    (select * from known_actual except select * from expected)
), ambiguous_departures as (
    select *
    from {{ ref('int_flight_timestamps') }}
    where flight_date >= '{{ var("phase3a_batch_start_date") }}'::date
      and flight_date < '{{ var("phase3a_batch_end_date") }}'::date
      and scheduled_departure_status = 'ambiguous_local_time'
), invalid_propagation as (
    select flight_record_key
    from ambiguous_departures
    where scheduled_departure_candidate_count <> 2
       or scheduled_departure_utc is not null
       or scheduled_arrival_status <> 'unresolved_ambiguous_departure'
       or scheduled_arrival_utc is not null
       or actual_departure_status <> case
            when is_cancelled then 'not_applicable_cancelled'
            else 'unresolved_ambiguous_scheduled_departure'
          end
       or actual_arrival_status <> case
            when is_cancelled then 'not_applicable_cancelled'
            when is_diverted then 'not_resolved_for_diversion'
            else 'unresolved_ambiguous_scheduled_departure'
          end
), incorrectly_audited as (
    select a.flight_record_key
    from {{ ref('audit_flight_timestamp_anomalies') }} a
    join ambiguous_departures d using (flight_record_key)
)
select stable_source_record_key, 'status_set_difference' as failure_reason from set_difference
union all
select flight_record_key, 'invalid_dst_ambiguity_propagation' from invalid_propagation
union all
select flight_record_key, 'dst_ambiguity_misclassified_as_source_anomaly' from incorrectly_audited
