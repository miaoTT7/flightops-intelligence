"""PostgreSQL metadata and atomic raw loading operations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from flightops.common.checksums import stream_sha256
from flightops.ingestion.errors import IngestionError
from flightops.ingestion.schema import DATABASE_COLUMNS
from flightops.ingestion.source import SourceInput
from flightops.ingestion.validation import Inspection, iter_validated_rows


DATASET_NAME = "bts_reporting_carrier_on_time_performance"


@dataclass(frozen=True)
class RegisteredSource:
    source_file_id: int
    already_succeeded: bool


def connect(dsn: str):
    """Open a psycopg connection, importing the optional driver lazily."""

    try:
        import psycopg
    except ImportError as exc:  # pragma: no cover - environment-specific
        raise IngestionError(
            "MISSING_DATABASE_DRIVER",
            "Install the project dependencies to provide psycopg",
            stage="database",
        ) from exc
    try:
        return psycopg.connect(dsn)
    except Exception as exc:
        raise IngestionError("DATABASE_CONNECTION", str(exc), stage="database") from exc


def apply_schema(connection: Any, sql_path: Path) -> None:
    """Apply the idempotent Phase 1.2 schema."""

    statement = sql_path.read_text(encoding="utf-8")
    with connection.transaction():
        connection.execute(statement)


def register_source(
    connection: Any,
    source: SourceInput,
    inspection: Inspection,
    relative_path: str,
) -> RegisteredSource:
    """Register content, rejecting a different file for an existing month."""

    existing = connection.execute(
        """
        SELECT source_file_id,
               EXISTS (
                   SELECT 1 FROM ingestion.ingestion_batch b
                   WHERE b.source_file_id = s.source_file_id AND b.status = 'succeeded'
               ) AS succeeded
        FROM ingestion.source_file s
        WHERE dataset_name = %s AND csv_sha256 = %s
        """,
        (DATASET_NAME, inspection.csv_sha256),
    ).fetchone()
    if existing:
        return RegisteredSource(int(existing[0]), bool(existing[1]))

    period_existing = connection.execute(
        """
        SELECT source_file_id, csv_sha256, original_filename
        FROM ingestion.source_file
        WHERE dataset_name = %s AND source_year = %s AND source_month = %s
        """,
        (DATASET_NAME, inspection.source_year, inspection.source_month),
    ).fetchone()
    if period_existing:
        raise IngestionError(
            "SOURCE_PERIOD_CONFLICT",
            f"{inspection.source_year}-{inspection.source_month:02d} already belongs to "
            f"{period_existing[2]} with CSV SHA-256 {period_existing[1]}",
            stage="registration",
        )

    row = connection.execute(
        """
        INSERT INTO ingestion.source_file (
            dataset_name, source_year, source_month, original_filename,
            first_seen_relative_path, csv_member_name, csv_sha256, csv_size_bytes,
            schema_fingerprint, expected_row_count, has_empty_trailing_column
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING source_file_id
        """,
        (
            DATASET_NAME,
            inspection.source_year,
            inspection.source_month,
            source.path.name,
            relative_path,
            source.csv_member_name,
            inspection.csv_sha256,
            inspection.csv_size_bytes,
            inspection.schema_fingerprint,
            inspection.row_count,
            inspection.has_empty_trailing_column,
        ),
    ).fetchone()
    return RegisteredSource(int(row[0]), False)


def create_batch(
    connection: Any,
    source_file_id: int,
    source: SourceInput,
    relative_path: str,
    status: str = "running",
) -> UUID:
    """Create an immutable attempt number and return its UUID."""

    batch_id = uuid4()
    attempt = connection.execute(
        """
        SELECT COALESCE(MAX(attempt_number), 0) + 1
        FROM ingestion.ingestion_batch
        WHERE source_file_id = %s
        """,
        (source_file_id,),
    ).fetchone()[0]
    connection.execute(
        """
        INSERT INTO ingestion.ingestion_batch (
            batch_id, source_file_id, attempt_number, status, input_filename,
            input_relative_path, container_type, archive_sha256, archive_size_bytes,
            completed_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s,
                  CASE WHEN %s = 'skipped' THEN clock_timestamp() ELSE NULL END)
        """,
        (
            batch_id,
            source_file_id,
            attempt,
            status,
            source.path.name,
            relative_path,
            source.container_type,
            source.archive_sha256,
            source.archive_size_bytes,
            status,
        ),
    )
    return batch_id


def mark_batch_failed(
    connection: Any,
    batch_id: UUID,
    error: Exception,
    rows_read: int = 0,
) -> None:
    """Record a rolled-back load failure in a separate transaction."""

    stage = error.stage if isinstance(error, IngestionError) else "load"
    error_type = error.code if isinstance(error, IngestionError) else type(error).__name__
    message = str(error)[:4000]
    with connection.transaction():
        connection.execute(
            """
            UPDATE ingestion.ingestion_batch
            SET status = 'failed', completed_at = clock_timestamp(), rows_read = %s,
                error_stage = %s, error_type = %s, error_message = %s
            WHERE batch_id = %s AND status = 'running'
            """,
            (rows_read, stage, error_type, message, batch_id),
        )


def atomic_load(
    connection: Any,
    source_file_id: int,
    batch_id: UUID,
    source: SourceInput,
    inspection: Inspection,
) -> int:
    """COPY raw rows and mark success together in one transaction."""

    column_definitions = ", ".join(f'"{column}" text' for column in DATABASE_COLUMNS)
    quoted_columns = ", ".join(f'"{column}"' for column in DATABASE_COLUMNS)
    row_count = 0
    with connection.transaction():
        # A period-level lock also protects against concurrent checksum variants.
        connection.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
            (f"{DATASET_NAME}:{inspection.source_year}:{inspection.source_month}",),
        )
        connection.execute(
            f"""
            CREATE TEMP TABLE bts_ingestion_stage (
                source_row_number bigint GENERATED ALWAYS AS IDENTITY,
                {column_definitions}
            ) ON COMMIT DROP
            """
        )
        copy_sql = f"COPY bts_ingestion_stage ({quoted_columns}) FROM STDIN"
        with connection.cursor() as cursor:
            with cursor.copy(copy_sql) as copy:
                for row_count, row in enumerate(
                    iter_validated_rows(
                        source,
                        expected_year=inspection.source_year,
                        expected_month=inspection.source_month,
                    ),
                    start=1,
                ):
                    copy.write_row(row)
        if row_count != inspection.row_count:
            raise IngestionError(
                "SOURCE_CHANGED",
                f"Preflight found {inspection.row_count} rows; load found {row_count}",
                stage="copy",
            )
        # Re-read with bounded memory before commit to detect replacement or
        # mutation between preflight inspection and COPY.
        with source.open_csv_binary() as binary:
            load_time_sha, _ = stream_sha256(binary)
        if load_time_sha != inspection.csv_sha256:
            raise IngestionError(
                "SOURCE_CHANGED",
                "CSV content changed between preflight and load",
                stage="copy",
            )
        connection.execute(
            f"""
            INSERT INTO raw.bts_on_time_performance (
                source_file_id, batch_id, source_row_number, {quoted_columns}
            )
            SELECT %s, %s, source_row_number, {quoted_columns}
            FROM bts_ingestion_stage
            ORDER BY source_row_number
            """,
            (source_file_id, batch_id),
        )
        updated = connection.execute(
            """
            UPDATE ingestion.ingestion_batch
            SET status = 'succeeded', completed_at = clock_timestamp(),
                rows_read = %s, rows_loaded = %s
            WHERE batch_id = %s AND status = 'running'
            """,
            (row_count, row_count, batch_id),
        ).rowcount
        if updated != 1:
            raise IngestionError(
                "BATCH_STATE_CONFLICT", str(batch_id), stage="commit"
            )
    return row_count
