with expected as (
    select flight_record_key from {{ ref('int_flight_timestamps') }}
    where flight_date >= '{{ var("phase3a_batch_start_date") }}'::date
      and flight_date < '{{ var("phase3a_batch_end_date") }}'::date
      and (scheduled_arrival_status = 'no_elapsed_consistent_candidate'
           or actual_arrival_status in ('local_round_trip_mismatch', 'arrival_delay_mismatch'))
), actual as (
    select flight_record_key from {{ ref('audit_flight_timestamp_anomalies') }}
    where flight_date >= '{{ var("phase3a_batch_start_date") }}'::date
      and flight_date < '{{ var("phase3a_batch_end_date") }}'::date
), coverage_difference as (
    (select * from expected except select * from actual)
    union all (select * from actual except select * from expected)
), invalid_explanations as (
    select flight_record_key from {{ ref('audit_flight_timestamp_anomalies') }}
    where flight_date >= '{{ var("phase3a_batch_start_date") }}'::date
      and flight_date < '{{ var("phase3a_batch_end_date") }}'::date
      and ((has_scheduled_elapsed_inconsistency
           and (scheduled_elapsed_error_minutes is null or scheduled_elapsed_error_minutes <= 1))
       or (actual_arrival_status = 'local_round_trip_mismatch'
           and (actual_elapsed_error_minutes is null or actual_elapsed_error_minutes <= 0))
       or (actual_arrival_status = 'arrival_delay_mismatch'
           and (arrival_delay_error_minutes is null or arrival_delay_error_minutes <= 1)))
)
select flight_record_key, 'coverage_difference' as failure_reason from coverage_difference
union all
select flight_record_key, 'invalid_semantic_explanation' from invalid_explanations
