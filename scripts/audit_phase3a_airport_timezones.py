#!/usr/bin/env python3
"""Independently compare Phase 3A airport zones with pinned geographic boundaries."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import zipfile
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_AIRPORTS_SHA = "f508467c19122ea549200daa215ea477eae2dc5375f339fd4e8226736c5981ea"
EXPECTED_BOUNDARY_SHA = "89dfbacb944fac18a2eb3be71f806c7486b791c01b61c0ce7ee3a7ee79dc1a61"
US_COUNTRIES = {"US", "PR", "VI", "GU", "MP", "AS"}
HISTORICAL_COORDINATE_ALIASES = {"PBI": "KPBI"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_env() -> dict[str, str]:
    env = os.environ.copy()
    path = ROOT / ".env"
    if path.exists():
        for raw_line in path.read_text().splitlines():
            line = raw_line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env.setdefault(key.strip(), value.strip().strip("\"").strip("'"))
    if not env.get("DATABASE_URL"):
        raise RuntimeError("DATABASE_URL is required")
    return env


def airport_mappings(dsn: str) -> list[dict[str, Any]]:
    import psycopg

    with psycopg.connect(dsn) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            select airport_id, airport_code, iana_timezone, mapping_method
            from analytics_phase3a.ref_airport_timezones
            order by airport_id
            """
        )
        return [
            {"airport_id": row[0], "airport_code": row[1], "mapped_timezone": row[2], "mapping_method": row[3]}
            for row in cursor.fetchall()
        ]


def coordinate_index(path: Path) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            code = row.get("iata_code", "").strip()
            if code and row.get("iso_country") in US_COUNTRIES:
                result[code].append(row)
            ident = row.get("ident", "").strip()
            if ident and row.get("iso_country") in US_COUNTRIES:
                result[f"IDENT:{ident}"].append(row)
    return result


def choose_coordinate(rows: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, str | None]:
    if not rows:
        return None, "missing_coordinate"
    scheduled = [row for row in rows if row.get("scheduled_service") == "yes"]
    candidates = scheduled or [row for row in rows if row.get("type") != "closed"]
    if len(candidates) != 1:
        return None, "ambiguous_coordinate"
    return candidates[0], None


def ring_contains(point: tuple[float, float], ring: list[list[float]]) -> bool:
    x, y = point
    inside = False
    previous_x, previous_y = ring[-1][:2]
    for coordinate in ring:
        current_x, current_y = coordinate[:2]
        if (current_y > y) != (previous_y > y):
            crossing_x = (previous_x - current_x) * (y - current_y) / (previous_y - current_y) + current_x
            if x < crossing_x:
                inside = not inside
        previous_x, previous_y = current_x, current_y
    return inside


def polygon_contains(point: tuple[float, float], polygon: list[list[list[float]]]) -> bool:
    return ring_contains(point, polygon[0]) and not any(ring_contains(point, hole) for hole in polygon[1:])


def geometry_polygons(geometry: dict[str, Any]) -> Iterable[list[list[list[float]]]]:
    if geometry["type"] == "Polygon":
        yield geometry["coordinates"]
    elif geometry["type"] == "MultiPolygon":
        yield from geometry["coordinates"]


def polygon_bbox(polygon: list[list[list[float]]]) -> tuple[float, float, float, float]:
    points = polygon[0]
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def load_boundaries(path: Path) -> list[tuple[str, tuple[float, float, float, float], list[list[list[float]]]]]:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if names != ["combined.json"]:
            raise RuntimeError(f"unexpected boundary archive members: {names}")
        with archive.open("combined.json") as handle:
            collection = json.load(handle)
    boundaries = []
    for feature in collection["features"]:
        tzid = feature["properties"]["tzid"]
        for polygon in geometry_polygons(feature["geometry"]):
            boundaries.append((tzid, polygon_bbox(polygon), polygon))
    return boundaries


def zones_at(point: tuple[float, float], boundaries) -> list[str]:
    x, y = point
    matches = {
        tzid
        for tzid, (minimum_x, minimum_y, maximum_x, maximum_y), polygon in boundaries
        if minimum_x <= x <= maximum_x and minimum_y <= y <= maximum_y
        and polygon_contains(point, polygon)
    }
    return sorted(matches)


def offset_equivalent(left: str, right: str) -> bool:
    left_zone, right_zone = ZoneInfo(left), ZoneInfo(right)
    instant = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = datetime(2026, 1, 1, tzinfo=timezone.utc)
    while instant < end:
        if instant.astimezone(left_zone).utcoffset() != instant.astimezone(right_zone).utcoffset():
            return False
        instant += timedelta(days=1)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--airports-csv", type=Path, required=True)
    parser.add_argument("--boundaries-zip", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "reports" / "phase3a_timezone_mapping_audit.json")
    args = parser.parse_args()
    airports_sha = sha256(args.airports_csv)
    boundaries_sha = sha256(args.boundaries_zip)
    if airports_sha != EXPECTED_AIRPORTS_SHA:
        raise RuntimeError(f"unexpected OurAirports SHA-256: {airports_sha}")
    if boundaries_sha != EXPECTED_BOUNDARY_SHA:
        raise RuntimeError(f"unexpected timezone boundary SHA-256: {boundaries_sha}")

    mappings = airport_mappings(load_env()["DATABASE_URL"])
    coordinates = coordinate_index(args.airports_csv)
    boundaries = load_boundaries(args.boundaries_zip)
    results, unresolved = [], []
    for mapping in mappings:
        coordinate_rows = coordinates.get(mapping["airport_code"], [])
        coordinate_method = "iata_code"
        if not coordinate_rows and mapping["airport_code"] in HISTORICAL_COORDINATE_ALIASES:
            alias = HISTORICAL_COORDINATE_ALIASES[mapping["airport_code"]]
            coordinate_rows = coordinates.get(f"IDENT:{alias}", [])
            coordinate_method = f"manual_historical_ident:{alias}"
        coordinate, coordinate_error = choose_coordinate(coordinate_rows)
        result = dict(mapping)
        if coordinate_error:
            result.update({"status": coordinate_error, "boundary_timezones": []})
            unresolved.append(result)
            results.append(result)
            continue
        latitude = float(coordinate["latitude_deg"])
        longitude = float(coordinate["longitude_deg"])
        boundary_zones = zones_at((longitude, latitude), boundaries)
        result.update({
            "latitude": latitude,
            "longitude": longitude,
            "coordinate_ident": coordinate["ident"],
            "coordinate_match_method": coordinate_method,
            "boundary_timezones": boundary_zones,
        })
        if mapping["mapped_timezone"] in boundary_zones:
            result["status"] = "exact_match"
        else:
            equivalents = [zone for zone in boundary_zones if offset_equivalent(mapping["mapped_timezone"], zone)]
            if len(boundary_zones) == 1 and equivalents:
                result["status"] = "offset_equivalent_alias"
                result["equivalent_boundary_timezone"] = equivalents[0]
            elif not boundary_zones:
                result["status"] = "no_boundary_polygon"
                unresolved.append(result)
            else:
                result["status"] = "timezone_mismatch"
                unresolved.append(result)
        results.append(result)

    status_counts: dict[str, int] = defaultdict(int)
    for result in results:
        status_counts[result["status"]] += 1
    report = {
        "status": "passed" if len(mappings) == 358 and not unresolved else "blocked",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "airports_checked": len(mappings),
        "unresolved_count": len(unresolved),
        "status_counts": dict(sorted(status_counts.items())),
        "sources": {
            "ourairports_commit": "2e34576752d971d8ce38b7187c6588e699535a29",
            "ourairports_sha256": airports_sha,
            "timezone_boundary_release": "2025b",
            "timezone_boundary_commit": "9d61564",
            "timezone_boundary_sha256": boundaries_sha,
            "timezone_boundary_license": "ODbL-1.0",
        },
        "unresolved": unresolved,
        "manual_coordinate_aliases": HISTORICAL_COORDINATE_ALIASES,
        "mappings": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: report[key] for key in ("status", "airports_checked", "unresolved_count", "status_counts")}, indent=2))
    return 0 if report["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
