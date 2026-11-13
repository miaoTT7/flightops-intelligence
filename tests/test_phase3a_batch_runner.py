from __future__ import annotations

import importlib.util
import json
from datetime import date
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "run_phase3a_utc_batches.py"
SPEC = importlib.util.spec_from_file_location("phase3a_batch_runner", SCRIPT)
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def test_month_range_is_inclusive_and_chronological() -> None:
    assert runner.month_range(date(2024, 11, 1), date(2025, 2, 1)) == [
        date(2024, 11, 1), date(2024, 12, 1),
        date(2025, 1, 1), date(2025, 2, 1),
    ]


def test_dbt_vars_is_exactly_one_month() -> None:
    assert json.loads(runner.dbt_vars(date(2025, 12, 1))) == {
        "phase3a_batch_start_date": "2025-12-01",
        "phase3a_batch_end_date": "2026-01-01",
    }


def test_timezone_audit_requires_zero_unresolved(tmp_path: Path) -> None:
    report = tmp_path / "audit.json"
    report.write_text(json.dumps({
        "status": "passed", "airports_checked": 358, "unresolved_count": 1,
    }))
    assert not runner.verify_timezone_audit(report)[0]

    report.write_text(json.dumps({
        "status": "passed", "airports_checked": 358, "unresolved_count": 0,
    }))
    assert runner.verify_timezone_audit(report)[0]
