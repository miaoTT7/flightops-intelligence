"""The source-to-raw schema contract for BTS on-time performance files."""

from __future__ import annotations

from hashlib import sha256


SOURCE_COLUMNS = [
    "Year", "Quarter", "Month", "DayofMonth", "DayOfWeek", "FlightDate",
    "Reporting_Airline", "DOT_ID_Reporting_Airline", "IATA_CODE_Reporting_Airline",
    "Tail_Number", "Flight_Number_Reporting_Airline", "OriginAirportID",
    "OriginAirportSeqID", "OriginCityMarketID", "Origin", "OriginCityName",
    "OriginState", "OriginStateFips", "OriginStateName", "OriginWac",
    "DestAirportID", "DestAirportSeqID", "DestCityMarketID", "Dest",
    "DestCityName", "DestState", "DestStateFips", "DestStateName", "DestWac",
    "CRSDepTime", "DepTime", "DepDelay", "DepDelayMinutes", "DepDel15",
    "DepartureDelayGroups", "DepTimeBlk", "TaxiOut", "WheelsOff", "WheelsOn",
    "TaxiIn", "CRSArrTime", "ArrTime", "ArrDelay", "ArrDelayMinutes", "ArrDel15",
    "ArrivalDelayGroups", "ArrTimeBlk", "Cancelled", "CancellationCode", "Diverted",
    "CRSElapsedTime", "ActualElapsedTime", "AirTime", "Flights", "Distance",
    "DistanceGroup", "CarrierDelay", "WeatherDelay", "NASDelay", "SecurityDelay",
    "LateAircraftDelay", "FirstDepTime", "TotalAddGTime", "LongestAddGTime",
    "DivAirportLandings", "DivReachedDest", "DivActualElapsedTime", "DivArrDelay",
    "DivDistance", "Div1Airport", "Div1AirportID", "Div1AirportSeqID",
    "Div1WheelsOn", "Div1TotalGTime", "Div1LongestGTime", "Div1WheelsOff",
    "Div1TailNum", "Div2Airport", "Div2AirportID", "Div2AirportSeqID",
    "Div2WheelsOn", "Div2TotalGTime", "Div2LongestGTime", "Div2WheelsOff",
    "Div2TailNum", "Div3Airport", "Div3AirportID", "Div3AirportSeqID",
    "Div3WheelsOn", "Div3TotalGTime", "Div3LongestGTime", "Div3WheelsOff",
    "Div3TailNum", "Div4Airport", "Div4AirportID", "Div4AirportSeqID",
    "Div4WheelsOn", "Div4TotalGTime", "Div4LongestGTime", "Div4WheelsOff",
    "Div4TailNum", "Div5Airport", "Div5AirportID", "Div5AirportSeqID",
    "Div5WheelsOn", "Div5TotalGTime", "Div5LongestGTime", "Div5WheelsOff",
    "Div5TailNum",
]


def _database_name(source_name: str) -> str:
    """Convert a source field to the project's stable PostgreSQL name."""

    special = {
        "DayofMonth": "day_of_month",
        "CRSDepTime": "crs_dep_time",
        "CRSArrTime": "crs_arr_time",
        "CRSElapsedTime": "crs_elapsed_time",
        "NASDelay": "nas_delay",
        "TotalAddGTime": "total_add_g_time",
        "LongestAddGTime": "longest_add_g_time",
    }
    for number in range(1, 6):
        special[f"Div{number}TotalGTime"] = f"div{number}_total_g_time"
        special[f"Div{number}LongestGTime"] = f"div{number}_longest_g_time"
    if source_name in special:
        return special[source_name]

    import re

    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", source_name)
    return value.lower()


DATABASE_COLUMNS = [_database_name(column) for column in SOURCE_COLUMNS]
SOURCE_TO_DATABASE = dict(zip(SOURCE_COLUMNS, DATABASE_COLUMNS, strict=True))
SCHEMA_FINGERPRINT = sha256("\x1f".join(SOURCE_COLUMNS).encode()).hexdigest()

assert len(SOURCE_COLUMNS) == 109
assert len(DATABASE_COLUMNS) == len(set(DATABASE_COLUMNS))

