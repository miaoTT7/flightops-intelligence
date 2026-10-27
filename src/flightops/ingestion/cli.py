"""Command-line interface for Phase 1.2 BTS ingestion."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from flightops.ingestion.database import apply_schema, connect
from flightops.ingestion.errors import IngestionError
from flightops.ingestion.service import ingest_path
from flightops.ingestion.source import discover_inputs


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SCHEMA_SQL = PROJECT_ROOT / "sql" / "001_phase1_ingestion.sql"


def _dsn(value: str | None) -> str:
    dsn = value or os.environ.get("DATABASE_URL")
    if not dsn:
        raise IngestionError(
            "DATABASE_URL_REQUIRED",
            "Pass --dsn or set DATABASE_URL",
            stage="configuration",
        )
    return dsn


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dsn", help="PostgreSQL DSN; defaults to DATABASE_URL")
    parser.add_argument("--verbose", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    init = subparsers.add_parser("init-db", help="Create the ingestion and raw tables")
    init.add_argument("--sql", type=Path, default=DEFAULT_SCHEMA_SQL)
    ingest = subparsers.add_parser("ingest", help="Ingest CSV/ZIP files or directories")
    ingest.add_argument("paths", nargs="+", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        dsn = _dsn(args.dsn)
        if args.command == "init-db":
            connection = connect(dsn)
            connection.autocommit = True
            try:
                apply_schema(connection, args.sql)
            finally:
                connection.close()
            print(f"Database schema applied from {args.sql}")
            return 0

        inputs = discover_inputs(args.paths)
        if not inputs:
            raise IngestionError(
                "NO_INPUTS", "No CSV or ZIP inputs were found", stage="discovery"
            )
        failures = 0
        for path in inputs:
            try:
                result = ingest_path(dsn, path, base_path=PROJECT_ROOT)
                print(
                    f"{result.status.upper()} {result.source_year}-{result.source_month:02d} "
                    f"rows={result.row_count:,} sha256={result.csv_sha256} "
                    f"batch={result.batch_id} file={path}"
                )
            except Exception as exc:
                failures += 1
                print(f"FAILED file={path}: {exc}", file=sys.stderr)
                if args.verbose:
                    import traceback

                    traceback.print_exc()
        return 1 if failures else 0
    except Exception as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        if getattr(args, "verbose", False):
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
