#!/usr/bin/env python3
"""Run guarded, resumable monthly Phase 3A UTC reconstruction batches."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DBT_DIR = ROOT / "dbt"
DBT = ROOT / ".venv" / "bin" / "dbt"
DEFAULT_CHECKPOINT = ROOT / ".phase3a" / "utc_batches_checkpoint.json"
DEFAULT_TZ_AUDIT = ROOT / "reports" / "phase3a_timezone_mapping_audit.json"
GIB = 1024**3
MIN_FREE_GIB = 10
TEST_SELECTORS = [
    "test_phase3a_timestamp_pilot_row_count",
    "test_phase3a_timestamp_pilot_preserves_lineage",
    "test_phase3a_timestamp_pilot_consistency",
    "test_phase3a_timestamp_pilot_timezone_coverage",
    "test_phase3a_timestamp_anomaly_audit_semantics",
    "test_phase3a_dst_fold_ambiguous_departure_propagation",
]
PREFLIGHT_SELECTORS = [
    "test_phase3a_airport_timezone_coverage",
    "test_phase3a_timezone_dst_rules",
    "test_phase3a_timestamp_sample_consistency",
    "test_phase3a_timestamp_sample_has_required_cases",
    "test_phase3a_timestamp_sample_preserves_lineage",
]


def parse_month(value: str) -> date:
    try:
        parsed = date.fromisoformat(f"{value}-01")
    except ValueError as exc:
        raise argparse.ArgumentTypeError("month must be YYYY-MM") from exc
    if not (date(2024, 1, 1) <= parsed <= date(2025, 12, 1)):
        raise argparse.ArgumentTypeError("month must be between 2024-01 and 2025-12")
    return parsed


def next_month(value: date) -> date:
    return date(value.year + (value.month == 12), value.month % 12 + 1, 1)


def month_key(value: date) -> str:
    return value.strftime("%Y-%m")


def month_range(start: date, end: date) -> list[date]:
    if end < start:
        raise ValueError("end month must not precede start month")
    result: list[date] = []
    current = start
    while current <= end:
        result.append(current)
        current = next_month(current)
    return result


def load_project_env() -> dict[str, str]:
    env = os.environ.copy()
    env_path = ROOT / ".env"
    if env_path.exists():
        for raw_line in env_path.read_text().splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env.setdefault(key.strip(), value.strip().strip("\"").strip("'"))
    if not env.get("DATABASE_URL"):
        raise RuntimeError("DATABASE_URL is required in the environment or project .env")
    return env


def load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    return json.loads(path.read_text())


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def db_connect(env: dict[str, str]):
    import psycopg

    # Control-plane reads must never hold relation locks while dbt subprocesses
    # replace the anomaly audit view or update the incremental target.
    return psycopg.connect(env["DATABASE_URL"], autocommit=True)


def scalar(connection, sql: str, params: tuple[Any, ...] = ()) -> Any:
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchone()[0]


def relation_exists(connection) -> bool:
    return bool(scalar(connection, "select to_regclass('analytics_phase3a.int_flight_timestamps') is not null"))


def input_rows(connection, month: date) -> int:
    return int(scalar(connection, "select count(*) from analytics_marts.fact_flights where flight_date >= %s and flight_date < %s", (month, next_month(month))))


def month_signature(connection, month: date) -> dict[str, Any]:
    if not relation_exists(connection):
        return {"rows": 0, "distinct_rows": 0, "key_signature": "0"}
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select count(*), count(distinct flight_record_key),
                   coalesce(sum(hashtextextended(flight_record_key, 0)::numeric), 0)::text
            from analytics_phase3a.int_flight_timestamps
            where flight_date >= %s and flight_date < %s
            """,
            (month, next_month(month)),
        )
        rows, distinct_rows, signature = cursor.fetchone()
    return {"rows": int(rows), "distinct_rows": int(distinct_rows), "key_signature": signature}


def month_metrics(connection, month: date) -> dict[str, Any]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select
                count(*) filter (where scheduled_departure_status='resolved_unique'),
                count(*) filter (where scheduled_arrival_status='resolved_unique'),
                count(*) filter (where actual_departure_status='validated'),
                count(*) filter (where actual_arrival_status='validated')
            from analytics_phase3a.int_flight_timestamps
            where flight_date >= %s and flight_date < %s
            """,
            (month, next_month(month)),
        )
        scheduled_departure, scheduled_arrival, actual_departure, actual_arrival = cursor.fetchone()
        cursor.execute(
            """
            select anomaly_classification, count(*)
            from analytics_phase3a.audit_flight_timestamp_anomalies
            where flight_date >= %s and flight_date < %s
            group by anomaly_classification order by anomaly_classification
            """,
            (month, next_month(month)),
        )
        anomalies = {name: count for name, count in cursor.fetchall()}
    return {
        "resolved": {
            "scheduled_departure": scheduled_departure,
            "scheduled_arrival": scheduled_arrival,
            "actual_departure": actual_departure,
            "actual_arrival": actual_arrival,
        },
        "anomalies": anomalies,
    }


def verify_timezone_audit(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, f"timezone audit report is missing: {path}"
    report = load_json(path, {})
    if report.get("status") != "passed":
        return False, f"timezone audit status is {report.get('status', 'missing')}"
    if report.get("airports_checked") != 358 or report.get("unresolved_count") != 0:
        return False, "timezone audit must verify exactly 358 airports with zero unresolved mappings"
    return True, "passed"


def run_command(command: list[str], env: dict[str, str]) -> float:
    display = " ".join(command)
    print(f"$ {display}", flush=True)
    started = time.monotonic()
    subprocess.run(command, cwd=DBT_DIR, env=env, check=True)
    return round(time.monotonic() - started, 3)


def dbt_vars(month: date) -> str:
    return json.dumps({
        "phase3a_batch_start_date": month.isoformat(),
        "phase3a_batch_end_date": next_month(month).isoformat(),
    })


def disk_safety(input_count: int) -> dict[str, Any]:
    free = shutil.disk_usage(ROOT).free
    projected_working = max(2 * GIB, input_count * 2048)
    required = MIN_FREE_GIB * GIB + projected_working
    return {
        "free_bytes": free,
        "projected_working_bytes": projected_working,
        "required_bytes": required,
        "safe": free >= required,
    }


def verify_completed(connection, checkpoint: dict[str, Any], month: date) -> bool:
    record = checkpoint.get("months", {}).get(month_key(month))
    if not record or record.get("status") != "complete":
        return False
    actual = month_signature(connection, month)
    if actual != record.get("signature"):
        raise RuntimeError(f"checkpoint/database mismatch for completed month {month_key(month)}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-month", type=parse_month, default=parse_month("2024-01"))
    parser.add_argument("--end-month", type=parse_month, default=parse_month("2025-12"))
    parser.add_argument("--batch-size", type=int, default=3)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--timezone-audit", type=Path, default=DEFAULT_TZ_AUDIT)
    parser.add_argument("--simulate-interruption-after", type=parse_month, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error("--batch-size must be positive")
    months = month_range(args.start_month, args.end_month)
    audit_ok, audit_message = verify_timezone_audit(args.timezone_audit)
    print(f"Phase 3A UTC plan: {len(months)} months, groups of {args.batch_size}")
    for index in range(0, len(months), args.batch_size):
        print("  batch:", ", ".join(month_key(m) for m in months[index:index + args.batch_size]))
    print(f"Timezone audit: {audit_message}")
    if args.dry_run:
        print("DRY RUN: no dbt or database mutations performed")
        return 0
    if not audit_ok:
        raise RuntimeError(f"real execution blocked: {audit_message}")

    env = load_project_env()
    checkpoint = load_json(args.checkpoint, {"version": 1, "months": {}})
    if not DBT.exists():
        raise RuntimeError(f"project dbt executable not found: {DBT}")

    with db_connect(env) as connection:
        run_command([
            str(DBT), "test", "--select", *PREFLIGHT_SELECTORS,
            "--vars", dbt_vars(months[0]), "--profiles-dir", ".",
        ], env)
        for index, month in enumerate(months, start=1):
            key = month_key(month)
            if args.resume and verify_completed(connection, checkpoint, month):
                print(f"[{index}/{len(months)}] {key}: verified complete; skipping")
                continue
            before_completed = {
                existing: month_signature(connection, parse_month(existing))
                for existing, record in checkpoint.get("months", {}).items()
                if record.get("status") == "complete" and existing != key
            }
            expected_input = input_rows(connection, month)
            disk = disk_safety(expected_input)
            if not disk["safe"]:
                raise RuntimeError(
                    f"unsafe disk capacity before {key}: free={disk['free_bytes']/GIB:.2f} GiB, "
                    f"required={disk['required_bytes']/GIB:.2f} GiB"
                )
            checkpoint.setdefault("months", {})[key] = {
                "status": "running", "input_rows": expected_input, "disk_before": disk
            }
            atomic_json(args.checkpoint, checkpoint)
            print(f"[{index}/{len(months)}] {key}: input={expected_input:,}, free={disk['free_bytes']/GIB:.2f} GiB")
            variables = dbt_vars(month)
            started = time.monotonic()
            try:
                run_seconds = run_command([
                    str(DBT), "run", "--select", "int_flight_timestamps",
                    "audit_flight_timestamp_anomalies", "--vars", variables,
                    "--profiles-dir", ".",
                ], env)
                selectors = TEST_SELECTORS.copy()
                if month == date(2025, 1, 1):
                    selectors.append("test_phase3a_timestamp_anomaly_expected_lineage")
                test_seconds = run_command([
                    str(DBT), "test", "--select", *selectors,
                    "--vars", variables, "--profiles-dir", ".",
                ], env)
                signature = month_signature(connection, month)
                if signature["rows"] != expected_input or signature["distinct_rows"] != signature["rows"]:
                    raise RuntimeError(f"row or unique-key reconciliation failed for {key}")
                for existing, expected_signature in before_completed.items():
                    if month_signature(connection, parse_month(existing)) != expected_signature:
                        raise RuntimeError(f"previously completed month changed: {existing}")
                metrics = month_metrics(connection, month)
                checkpoint["months"][key] = {
                    "status": "complete",
                    "input_rows": expected_input,
                    "output_rows": signature["rows"],
                    "signature": signature,
                    "metrics": metrics,
                    "run_seconds": run_seconds,
                    "test_seconds": test_seconds,
                    "total_seconds": round(time.monotonic() - started, 3),
                    "disk_before": disk,
                    "free_bytes_after": shutil.disk_usage(ROOT).free,
                    "tests": "passed",
                }
                atomic_json(args.checkpoint, checkpoint)
            except BaseException:
                checkpoint["months"][key]["status"] = "failed"
                checkpoint["months"][key]["total_seconds"] = round(time.monotonic() - started, 3)
                atomic_json(args.checkpoint, checkpoint)
                raise
            if args.simulate_interruption_after == month:
                print(f"Simulated interruption after verified completion of {key}")
                return 75
        if months == month_range(date(2024, 1, 1), date(2025, 12, 1)):
            core_total = int(scalar(connection, "select count(*) from analytics_marts.fact_flights"))
            target_total = int(scalar(connection, "select count(*) from analytics_phase3a.int_flight_timestamps"))
            target_distinct = int(scalar(connection, "select count(distinct flight_record_key) from analytics_phase3a.int_flight_timestamps"))
            covered_months = int(scalar(connection, "select count(distinct date_trunc('month', flight_date)) from analytics_phase3a.int_flight_timestamps"))
            if core_total != target_total or target_distinct != target_total or covered_months != 24:
                raise RuntimeError(
                    f"final reconciliation failed: core={core_total}, target={target_total}, "
                    f"distinct={target_distinct}, months={covered_months}"
                )
    print("Requested Phase 3A UTC schedule completed successfully")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
