"""Application service coordinating inspection, lineage, and atomic loading."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from flightops.ingestion.database import (
    DATASET_NAME,
    atomic_load,
    connect,
    create_batch,
    mark_batch_failed,
    register_source,
)
from flightops.ingestion.source import prepare_source
from flightops.ingestion.validation import inspect_source


@dataclass(frozen=True)
class IngestionResult:
    path: Path
    source_file_id: int
    batch_id: UUID
    status: str
    row_count: int
    csv_sha256: str
    source_year: int
    source_month: int


def display_path(path: Path, base: Path | None = None) -> str:
    """Prefer portable relative lineage paths without hiding external names."""

    root = (base or Path.cwd()).resolve()
    try:
        return str(path.resolve().relative_to(root))
    except ValueError:
        return path.name


def ingest_path(dsn: str, path: str | Path, *, base_path: Path | None = None) -> IngestionResult:
    """Inspect and ingest one source path, or record an idempotent skip."""

    source = prepare_source(path)
    inspection = inspect_source(source)
    relative_path = display_path(source.path, base_path)
    connection = connect(dsn)
    connection.autocommit = True
    try:
        with connection.transaction():
            connection.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                (f"{DATASET_NAME}:{inspection.source_year}:{inspection.source_month}",),
            )
            registered = register_source(connection, source, inspection, relative_path)
            if registered.already_succeeded:
                batch_id = create_batch(
                    connection,
                    registered.source_file_id,
                    source,
                    relative_path,
                    status="skipped",
                )
                return IngestionResult(
                    source.path,
                    registered.source_file_id,
                    batch_id,
                    "skipped",
                    0,
                    inspection.csv_sha256,
                    inspection.source_year,
                    inspection.source_month,
                )
            batch_id = create_batch(
                connection, registered.source_file_id, source, relative_path
            )

        try:
            loaded = atomic_load(
                connection,
                registered.source_file_id,
                batch_id,
                source,
                inspection,
            )
        except Exception as exc:
            mark_batch_failed(
                connection,
                batch_id,
                exc,
                rows_read=int(getattr(exc, "rows_read", 0)),
            )
            raise
        return IngestionResult(
            source.path,
            registered.source_file_id,
            batch_id,
            "succeeded",
            loaded,
            inspection.csv_sha256,
            inspection.source_year,
            inspection.source_month,
        )
    finally:
        connection.close()
