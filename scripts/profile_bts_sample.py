#!/usr/bin/env python3
"""Generate the Phase 1.1 BTS profile from an untouched source CSV."""

# Automation Script
from __future__ import annotations
import argparse
from pathlib import Path

from flightops.profiling.bts import profile_bts_csv, render_markdown_report


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = PROJECT_ROOT / "data" / "raw" / "bts"
DEFAULT_REPORT = PROJECT_ROOT / "reports" / "phase1_data_profile.md"


def find_single_csv(directory: Path) -> Path:
    """Return the only CSV below *directory*, failing on ambiguity."""

    matches = sorted(directory.rglob("*.csv"))
    if len(matches) != 1:
        raise ValueError(
            f"Expected exactly one CSV below {directory}, found {len(matches)}"
        )
    return matches[0]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--csv",
        type=Path,
        help="BTS CSV path; defaults to the only CSV under data/raw/bts",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    csv_path = args.csv or find_single_csv(DEFAULT_DATA_DIR)
    profile = profile_bts_csv(csv_path)
    report = render_markdown_report(profile)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(f"Profiled {profile['row_count']:,} rows from {csv_path}")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()

