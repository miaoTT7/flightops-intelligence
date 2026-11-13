with checks as (
    select
        -- New York springs forward: 01:30 EST -> 06:30 UTC and 03:30 EDT -> 07:30 UTC.
        timestamp '2024-03-10 01:30' at time zone 'America/New_York'
            = timestamptz '2024-03-10 06:30+00' as spring_before,
        timestamp '2024-03-10 03:30' at time zone 'America/New_York'
            = timestamptz '2024-03-10 07:30+00' as spring_after,
        -- 02:30 is in the spring gap and must not round-trip to itself.
        ((timestamp '2024-03-10 02:30' at time zone 'America/New_York')
            at time zone 'America/New_York') <> timestamp '2024-03-10 02:30'
            as spring_gap_detected,
        -- Both UTC candidates round-trip to the repeated 01:30 during fall-back.
        (timestamptz '2024-11-03 05:30+00' at time zone 'America/New_York')
            = timestamp '2024-11-03 01:30'
          and (timestamptz '2024-11-03 06:30+00' at time zone 'America/New_York')
            = timestamp '2024-11-03 01:30' as fall_fold_detected,
        -- Repeat a 2025 boundary to guard the full project period.
        timestamp '2025-03-09 03:30' at time zone 'America/New_York'
            = timestamptz '2025-03-09 07:30+00' as rules_2025
)
select 'iana_dst_rule_failure' as failure_reason
from checks
where not (spring_before and spring_after and spring_gap_detected
           and fall_fold_detected and rules_2025)

