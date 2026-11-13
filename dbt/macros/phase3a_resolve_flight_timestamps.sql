{% macro phase3a_resolve_flight_timestamps(input_relation, extra_columns=[]) -%}
localized as (
    select
        f.*,
        o.iana_timezone as origin_iana_timezone,
        d.iana_timezone as destination_iana_timezone,
        flight_date + scheduled_departure_day_offset + scheduled_departure_time as scheduled_departure_local,
        flight_date + scheduled_arrival_day_offset + scheduled_arrival_time as scheduled_arrival_local_base
    from {{ input_relation }} f
    left join {{ ref('ref_airport_timezones') }} o on f.origin_airport_id = o.airport_id
    left join {{ ref('ref_airport_timezones') }} d on f.destination_airport_id = d.airport_id
),
departure_candidates as (
    select l.flight_record_key, c.utc_candidate
    from localized l
    cross join lateral (
        select distinct candidate as utc_candidate
        from unnest(array[
            l.scheduled_departure_local at time zone l.origin_iana_timezone,
            (l.scheduled_departure_local at time zone l.origin_iana_timezone) - interval '1 hour',
            (l.scheduled_departure_local at time zone l.origin_iana_timezone) + interval '1 hour'
        ]) candidate
        where candidate at time zone l.origin_iana_timezone = l.scheduled_departure_local
    ) c
),
departure_resolution as (
    select flight_record_key, count(*) as departure_candidate_count,
           min(utc_candidate) as unique_departure_utc
    from departure_candidates
    group by flight_record_key
),
arrival_candidates as (
    select
        l.flight_record_key,
        c.utc_candidate,
        extract(epoch from (c.utc_candidate - dr.unique_departure_utc)) / 60.0
            as implied_elapsed_minutes
    from localized l
    join departure_resolution dr using (flight_record_key)
    cross join generate_series(-1, 2) date_shift
    cross join lateral (
        select distinct candidate as utc_candidate
        from unnest(array[
            (l.scheduled_arrival_local_base + date_shift * interval '1 day') at time zone l.destination_iana_timezone,
            ((l.scheduled_arrival_local_base + date_shift * interval '1 day') at time zone l.destination_iana_timezone) - interval '1 hour',
            ((l.scheduled_arrival_local_base + date_shift * interval '1 day') at time zone l.destination_iana_timezone) + interval '1 hour'
        ]) candidate
        where candidate at time zone l.destination_iana_timezone
            = l.scheduled_arrival_local_base + date_shift * interval '1 day'
    ) c
    where dr.departure_candidate_count = 1
      and l.is_scheduled_elapsed_time_valid
      and abs(extract(epoch from (c.utc_candidate - dr.unique_departure_utc)) / 60.0
              - l.scheduled_elapsed_minutes) <= 1
),
arrival_resolution as (
    select flight_record_key, count(*) as arrival_candidate_count,
           min(utc_candidate) as unique_arrival_utc,
           min(abs(implied_elapsed_minutes)) as implied_scheduled_elapsed_minutes
    from arrival_candidates
    group by flight_record_key
),
resolved as (
    select
        l.*,
        coalesce(dr.departure_candidate_count, 0) as scheduled_departure_candidate_count,
        case when dr.departure_candidate_count = 1 then dr.unique_departure_utc end as scheduled_departure_utc,
        coalesce(ar.arrival_candidate_count, 0) as scheduled_arrival_candidate_count,
        case when ar.arrival_candidate_count = 1 then ar.unique_arrival_utc end as scheduled_arrival_utc,
        case
            when l.origin_iana_timezone is null then 'missing_timezone'
            when l.scheduled_departure_local is null then 'missing_local_time'
            when coalesce(dr.departure_candidate_count, 0) = 0 then 'nonexistent_local_time'
            when dr.departure_candidate_count > 1 then 'ambiguous_local_time'
            else 'resolved_unique'
        end as scheduled_departure_status,
        case
            when l.destination_iana_timezone is null then 'missing_timezone'
            when l.scheduled_arrival_local_base is null then 'missing_local_time'
            when dr.departure_candidate_count > 1 then 'unresolved_ambiguous_departure'
            when l.is_scheduled_elapsed_time_valid is null then 'missing_elapsed'
            when not l.is_scheduled_elapsed_time_valid then 'invalid_elapsed'
            when coalesce(ar.arrival_candidate_count, 0) = 0 then 'no_elapsed_consistent_candidate'
            when ar.arrival_candidate_count > 1 then 'ambiguous_elapsed_consistent_candidates'
            else 'resolved_unique'
        end as scheduled_arrival_status
    from localized l
    left join departure_resolution dr using (flight_record_key)
    left join arrival_resolution ar using (flight_record_key)
),
actual_derived as (
    select
        r.*,
        case when scheduled_departure_utc is not null and departure_delay_minutes_signed is not null
             then scheduled_departure_utc + departure_delay_minutes_signed * interval '1 minute'
        end as actual_departure_utc,
        case when scheduled_departure_utc is not null
                   and departure_delay_minutes_signed is not null
                   and is_actual_elapsed_time_valid
             then scheduled_departure_utc + departure_delay_minutes_signed * interval '1 minute'
                  + actual_elapsed_minutes * interval '1 minute'
        end as actual_arrival_utc
    from resolved r
)
select
    flight_record_key, source_file_id, source_row_number, batch_id, ingested_at,
    {% for column in extra_columns %}{{ column }},{% endfor %}
    flight_date, reporting_airline_code, flight_number, tail_number,
    origin_airport_key, origin_airport_id, origin_airport_code, origin_iana_timezone,
    destination_airport_key, destination_airport_id, destination_airport_code, destination_iana_timezone,
    scheduled_departure_time, scheduled_departure_day_offset, scheduled_departure_local,
    scheduled_departure_candidate_count, scheduled_departure_status, scheduled_departure_utc,
    scheduled_arrival_time, scheduled_arrival_day_offset, scheduled_arrival_local_base,
    scheduled_elapsed_minutes, is_scheduled_elapsed_time_valid,
    scheduled_arrival_candidate_count, scheduled_arrival_status, scheduled_arrival_utc,
    actual_departure_time, actual_departure_day_offset, departure_delay_minutes_signed,
    actual_departure_utc,
    actual_arrival_time, actual_arrival_day_offset, arrival_delay_minutes_signed,
    actual_elapsed_minutes, is_actual_elapsed_time_valid, actual_arrival_utc,
    is_cancelled, is_diverted,
    case
        when actual_departure_utc is null then
            case
                when is_cancelled then 'not_applicable_cancelled'
                when scheduled_departure_status = 'ambiguous_local_time'
                    then 'unresolved_ambiguous_scheduled_departure'
                else 'missing_inputs'
            end
        when actual_departure_time is null then 'missing_reported_local_time'
        when (actual_departure_utc at time zone origin_iana_timezone)::time <> actual_departure_time
            then 'local_round_trip_mismatch'
        else 'validated'
    end as actual_departure_status,
    case
        when actual_arrival_utc is null then
            case
                when is_cancelled then 'not_applicable_cancelled'
                when is_diverted then 'not_resolved_for_diversion'
                when scheduled_departure_status = 'ambiguous_local_time'
                    then 'unresolved_ambiguous_scheduled_departure'
                else 'missing_or_invalid_elapsed'
            end
        when actual_arrival_time is null then 'missing_reported_local_time'
        when (actual_arrival_utc at time zone destination_iana_timezone)::time <> actual_arrival_time
            then 'local_round_trip_mismatch'
        when scheduled_arrival_utc is not null and arrival_delay_minutes_signed is not null
         and abs(extract(epoch from (actual_arrival_utc - scheduled_arrival_utc)) / 60.0
                 - arrival_delay_minutes_signed) > 1
            then 'arrival_delay_mismatch'
        else 'validated'
    end as actual_arrival_status
from actual_derived
{%- endmacro %}
