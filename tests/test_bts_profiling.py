from __future__ import annotations

import pandas as pd

from flightops.profiling.bts import (
    assess_tail_sequences,
    hhmm_to_minutes,
    local_datetime,
    profile_dataframe,
)


def test_hhmm_to_minutes_accepts_midnight_and_2400_and_rejects_invalid() -> None:
    values = pd.Series([0, 5, 45, 1234, 2359, 2400, 2360, 2500, -1, None])

    result = hhmm_to_minutes(values)

    assert result.iloc[:6].tolist() == [0.0, 5.0, 45.0, 754.0, 1439.0, 1440.0]
    assert result.iloc[6:].isna().all()


def test_local_datetime_advances_2400_to_next_day() -> None:
    result = local_datetime(pd.Series(["2024-01-31"]), pd.Series([2400]))

    assert result.iloc[0] == pd.Timestamp("2024-02-01 00:00:00")


def test_profile_counts_full_duplicates_and_candidate_key_collisions() -> None:
    base = {
        "FlightDate": "2024-01-01",
        "Reporting_Airline": "ZZ",
        "Flight_Number_Reporting_Airline": 10,
        "Origin": "AAA",
        "Dest": "BBB",
        "CRSDepTime": 800,
        "CRSArrTime": 900,
        "Tail_Number": "N1",
        "Cancelled": 0,
        "Diverted": 0,
    }
    frame = pd.DataFrame([base, base, {**base, "Tail_Number": "N2"}])

    result = profile_dataframe(frame)

    assert result["exact_duplicate_rows"] == 2
    assert result["exact_duplicate_excess"] == 1
    assert result["candidate_key_duplicate_rows"] == 3


def test_tail_sequence_requires_airport_continuity_and_valid_ground_time() -> None:
    frame = pd.DataFrame(
        [
            {
                "Tail_Number": "N1",
                "FlightDate": "2024-01-01",
                "Origin": "AAA",
                "Dest": "BBB",
                "CRSDepTime": 2200,
                "CRSArrTime": 2330,
            },
            {
                "Tail_Number": "N1",
                "FlightDate": "2024-01-02",
                "Origin": "BBB",
                "Dest": "CCC",
                "CRSDepTime": 30,
                "CRSArrTime": 200,
            },
            {
                "Tail_Number": "N1",
                "FlightDate": "2024-01-02",
                "Origin": "DDD",
                "Dest": "EEE",
                "CRSDepTime": 400,
                "CRSArrTime": 500,
            },
        ]
    )

    result = assess_tail_sequences(frame)

    assert result["adjacent_same_tail_pairs"] == 2
    assert result["airport_continuous_pairs"] == 1
    assert result["plausible_connections_0_to_24h"] == 1


def test_overnight_arrival_is_used_for_connection_ground_time() -> None:
    frame = pd.DataFrame(
        [
            {
                "Tail_Number": "N1",
                "FlightDate": "2024-01-01",
                "Origin": "AAA",
                "Dest": "BBB",
                "CRSDepTime": 2300,
                "CRSArrTime": 30,
            },
            {
                "Tail_Number": "N1",
                "FlightDate": "2024-01-02",
                "Origin": "BBB",
                "Dest": "CCC",
                "CRSDepTime": 130,
                "CRSArrTime": 300,
            },
        ]
    )

    result = assess_tail_sequences(frame)

    assert result["plausible_connections_0_to_24h"] == 1


def test_tail_sequence_reports_missing_tail_cancellation_overlap() -> None:
    frame = pd.DataFrame(
        [
            {
                "Tail_Number": None,
                "FlightDate": "2024-01-01",
                "Origin": "AAA",
                "Dest": "BBB",
                "CRSDepTime": 800,
                "CRSArrTime": 900,
                "Cancelled": 1,
            },
            {
                "Tail_Number": "N1",
                "FlightDate": "2024-01-01",
                "Origin": "AAA",
                "Dest": "BBB",
                "CRSDepTime": 1000,
                "CRSArrTime": 1100,
                "Cancelled": 0,
            },
        ]
    )

    result = assess_tail_sequences(frame)

    assert result["rows_without_tail"] == 1
    assert result["rows_without_tail_cancelled"] == 1
