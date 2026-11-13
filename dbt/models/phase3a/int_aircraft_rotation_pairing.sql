{{ config(materialized='table', schema='phase3a') }}

-- One row per flight. Candidate successors are the immediately following
-- record for the same reported tail in scheduled UTC order. We never skip an
-- intervening leg to manufacture airport continuity.
with flights as (
    select
        flight_record_key, flight_date, reporting_airline_code, flight_number,
        nullif(btrim(tail_number), '') as tail_number,
        origin_airport_id, origin_airport_code,
        destination_airport_id, destination_airport_code,
        scheduled_departure_utc, scheduled_arrival_utc,
        actual_departure_utc, actual_arrival_utc,
        scheduled_departure_status, scheduled_arrival_status,
        actual_departure_status, actual_arrival_status,
        departure_delay_minutes_signed, arrival_delay_minutes_signed,
        is_cancelled, is_diverted
    from {{ ref('int_flight_timestamps') }}
),
tail_rows as (
    select
        *,
        count(*) over (
            partition by tail_number, scheduled_departure_utc
        ) as scheduled_departure_peer_count
    from flights
    where tail_number is not null
),
sequenced as (
    select
        *,
        lead(flight_record_key) over rotation_order as next_flight_record_key,
        lead(flight_date) over rotation_order as next_flight_date,
        lead(reporting_airline_code) over rotation_order as next_reporting_airline_code,
        lead(flight_number) over rotation_order as next_flight_number,
        lead(origin_airport_id) over rotation_order as next_origin_airport_id,
        lead(origin_airport_code) over rotation_order as next_origin_airport_code,
        lead(destination_airport_id) over rotation_order as next_destination_airport_id,
        lead(destination_airport_code) over rotation_order as next_destination_airport_code,
        lead(scheduled_departure_utc) over rotation_order as next_scheduled_departure_utc,
        lead(scheduled_arrival_utc) over rotation_order as next_scheduled_arrival_utc,
        lead(actual_departure_utc) over rotation_order as next_actual_departure_utc,
        lead(scheduled_departure_status) over rotation_order as next_scheduled_departure_status,
        lead(scheduled_arrival_status) over rotation_order as next_scheduled_arrival_status,
        lead(actual_departure_status) over rotation_order as next_actual_departure_status,
        lead(departure_delay_minutes_signed) over rotation_order as next_departure_delay_minutes_signed,
        lead(is_cancelled) over rotation_order as next_is_cancelled,
        lead(is_diverted) over rotation_order as next_is_diverted,
        lead(scheduled_departure_peer_count) over rotation_order as next_scheduled_departure_peer_count
    from tail_rows
    window rotation_order as (
        partition by tail_number
        order by scheduled_departure_utc nulls last, flight_record_key
    )
),
candidates as (
    select
        f.*,
        s.scheduled_departure_peer_count,
        s.next_flight_record_key, s.next_flight_date,
        s.next_reporting_airline_code, s.next_flight_number,
        s.next_origin_airport_id, s.next_origin_airport_code,
        s.next_destination_airport_id, s.next_destination_airport_code,
        s.next_scheduled_departure_utc, s.next_scheduled_arrival_utc,
        s.next_actual_departure_utc,
        s.next_scheduled_departure_status, s.next_scheduled_arrival_status,
        s.next_actual_departure_status,
        s.next_departure_delay_minutes_signed,
        s.next_is_cancelled, s.next_is_diverted,
        s.next_scheduled_departure_peer_count,
        extract(epoch from (s.next_scheduled_departure_utc - f.scheduled_arrival_utc)) / 60.0
            as scheduled_turnaround_minutes,
        extract(epoch from (s.next_actual_departure_utc - f.actual_arrival_utc)) / 60.0
            as actual_ground_minutes
    from flights f
    left join sequenced s using (flight_record_key)
),
classified as (
    select
        *,
        case
            when tail_number is null then 'missing_tail_number'
            when is_cancelled then 'previous_cancelled'
            when is_diverted then 'previous_diverted'
            when scheduled_departure_status <> 'resolved_unique' then 'previous_scheduled_departure_unresolved'
            when scheduled_arrival_status <> 'resolved_unique' then 'previous_scheduled_arrival_unresolved'
            when actual_arrival_status <> 'validated' then 'previous_actual_arrival_unvalidated'
            when scheduled_departure_peer_count > 1 then 'ambiguous_scheduled_departure_tie'
            when next_flight_record_key is null then 'no_next_flight_in_data'
            when next_is_cancelled then 'next_cancelled'
            when next_is_diverted then 'next_diverted'
            when next_scheduled_departure_status <> 'resolved_unique' then 'next_scheduled_departure_unresolved'
            when next_scheduled_arrival_status <> 'resolved_unique' then 'next_scheduled_arrival_unresolved'
            when next_actual_departure_status <> 'validated' then 'next_actual_departure_unvalidated'
            when next_scheduled_departure_peer_count > 1 then 'ambiguous_next_scheduled_departure_tie'
            when destination_airport_id <> next_origin_airport_id then 'airport_discontinuity'
            when scheduled_turnaround_minutes <= 0 then 'nonpositive_scheduled_turnaround'
            when scheduled_turnaround_minutes < 20 then 'below_primary_turnaround_window'
            when scheduled_turnaround_minutes > 360 then 'above_primary_turnaround_window'
            when actual_ground_minutes < 0 then 'negative_actual_ground_time'
            else 'matched'
        end as rotation_exclusion_reason
    from candidates
)
select
    flight_record_key as previous_flight_record_key,
    flight_date as previous_flight_date,
    reporting_airline_code as previous_reporting_airline_code,
    flight_number as previous_flight_number,
    tail_number,
    origin_airport_id as previous_origin_airport_id,
    origin_airport_code as previous_origin_airport_code,
    destination_airport_id as connection_airport_id,
    destination_airport_code as connection_airport_code,
    scheduled_departure_utc as previous_scheduled_departure_utc,
    scheduled_arrival_utc as previous_scheduled_arrival_utc,
    actual_arrival_utc as previous_actual_arrival_utc,
    arrival_delay_minutes_signed as previous_arrival_delay_minutes_signed,
    next_flight_record_key,
    next_flight_date,
    next_reporting_airline_code,
    next_flight_number,
    next_origin_airport_id,
    next_origin_airport_code,
    next_destination_airport_id,
    next_destination_airport_code,
    next_scheduled_departure_utc,
    next_scheduled_arrival_utc,
    next_actual_departure_utc,
    next_departure_delay_minutes_signed,
    scheduled_turnaround_minutes,
    actual_ground_minutes,
    coalesce(date_trunc('month', flight_date) <> date_trunc('month', next_flight_date), false)
        as is_cross_month_connection,
    case when rotation_exclusion_reason = 'matched' then 'matched' else 'unmatched' end
        as rotation_match_status,
    rotation_exclusion_reason
from classified

