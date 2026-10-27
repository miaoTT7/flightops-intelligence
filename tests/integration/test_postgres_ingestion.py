from __future__ import annotations

import csv
import os
from pathlib import Path
from zipfile import ZipFile

import pytest

psycopg = pytest.importorskip("psycopg")

from flightops.ingestion.database import (
    apply_schema,
    atomic_load,
    connect,
    create_batch,
    mark_batch_failed,
    register_source,
)
from flightops.ingestion.errors import IngestionError
from flightops.ingestion.schema import SOURCE_COLUMNS
from flightops.ingestion.service import display_path, ingest_path
from flightops.ingestion.source import prepare_source
from flightops.ingestion.validation import inspect_source


pytestmark = pytest.mark.integration


def _dsn() -> str:
    value = os.environ.get("TEST_DATABASE_URL")
    if not value:
        pytest.skip("TEST_DATABASE_URL is not set")
    return value


def _write_fixture(path: Path, *, year: int = 2099, month: int = 12) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow([*SOURCE_COLUMNS, ""])
        for day in (1, 2):
            row = [""] * len(SOURCE_COLUMNS)
            row[SOURCE_COLUMNS.index("Year")] = str(year)
            row[SOURCE_COLUMNS.index("Month")] = str(month)
            row[SOURCE_COLUMNS.index("DayofMonth")] = str(day)
            row[SOURCE_COLUMNS.index("FlightDate")] = f"{year}-{month:02d}-{day:02d}"
            row[SOURCE_COLUMNS.index("Reporting_Airline")] = "ZZ"
            row[SOURCE_COLUMNS.index("Origin")] = "AAA"
            row[SOURCE_COLUMNS.index("Dest")] = "BBB"
            writer.writerow([*row, ""])


@pytest.fixture
def prepared_database():
    dsn = _dsn()
    connection = connect(dsn)
    connection.autocommit = True
    sql_path = Path(__file__).resolve().parents[2] / "sql" / "001_phase1_ingestion.sql"
    apply_schema(connection, sql_path)
    connection.execute(
        """
        DELETE FROM raw.bts_on_time_performance
        WHERE source_file_id IN (
            SELECT source_file_id FROM ingestion.source_file
            WHERE source_year = 2099 AND source_month = 12
        )
        """
    )
    connection.execute(
        """
        DELETE FROM ingestion.ingestion_batch
        WHERE source_file_id IN (
            SELECT source_file_id FROM ingestion.source_file
            WHERE source_year = 2099 AND source_month = 12
        )
        """
    )
    connection.execute(
        "DELETE FROM ingestion.source_file WHERE source_year = 2099 AND source_month = 12"
    )
    connection.close()
    yield dsn
    connection = connect(dsn)
    connection.autocommit = True
    connection.execute(
        """
        DELETE FROM raw.bts_on_time_performance
        WHERE source_file_id IN (
            SELECT source_file_id FROM ingestion.source_file
            WHERE source_year = 2099 AND source_month = 12
        )
        """
    )
    connection.execute(
        """
        DELETE FROM ingestion.ingestion_batch
        WHERE source_file_id IN (
            SELECT source_file_id FROM ingestion.source_file
            WHERE source_year = 2099 AND source_month = 12
        )
        """
    )
    connection.execute(
        "DELETE FROM ingestion.source_file WHERE source_year = 2099 AND source_month = 12"
    )
    connection.close()


def test_success_then_same_csv_content_in_zip_is_skipped(
    tmp_path: Path, prepared_database: str
) -> None:
    csv_path = tmp_path / "fixture.csv"
    _write_fixture(csv_path)
    zip_path = tmp_path / "fixture.zip"
    with ZipFile(zip_path, "w") as archive:
        archive.write(csv_path, "data/renamed.csv")
        archive.writestr("readme.html", "metadata")

    first = ingest_path(prepared_database, csv_path)
    second = ingest_path(prepared_database, zip_path)

    assert first.status == "succeeded"
    assert first.row_count == 2
    assert second.status == "skipped"
    assert second.source_file_id == first.source_file_id
    connection = connect(prepared_database)
    raw_count = connection.execute(
        "SELECT count(*) FROM raw.bts_on_time_performance WHERE source_file_id = %s",
        (first.source_file_id,),
    ).fetchone()[0]
    statuses = connection.execute(
        """
        SELECT status FROM ingestion.ingestion_batch
        WHERE source_file_id = %s ORDER BY attempt_number
        """,
        (first.source_file_id,),
    ).fetchall()
    connection.close()
    assert raw_count == 2
    assert [row[0] for row in statuses] == ["succeeded", "skipped"]


def test_failed_copy_rolls_back_raw_rows_and_records_failed_batch(
    tmp_path: Path, prepared_database: str
) -> None:
    csv_path = tmp_path / "changes_during_load.csv"
    _write_fixture(csv_path)
    source = prepare_source(csv_path)
    inspection = inspect_source(source)
    relative_path = display_path(csv_path, tmp_path)
    connection = connect(prepared_database)
    connection.autocommit = True
    with connection.transaction():
        registered = register_source(connection, source, inspection, relative_path)
        batch_id = create_batch(
            connection, registered.source_file_id, source, relative_path
        )

    # Simulate a source being replaced after preflight but before COPY.
    _write_fixture(csv_path, year=2099, month=11)
    with pytest.raises(IngestionError) as captured:
        atomic_load(
            connection,
            registered.source_file_id,
            batch_id,
            source,
            inspection,
        )
    mark_batch_failed(connection, batch_id, captured.value)

    raw_count = connection.execute(
        "SELECT count(*) FROM raw.bts_on_time_performance WHERE source_file_id = %s",
        (registered.source_file_id,),
    ).fetchone()[0]
    batch = connection.execute(
        "SELECT status, error_type FROM ingestion.ingestion_batch WHERE batch_id = %s",
        (batch_id,),
    ).fetchone()
    connection.close()
    assert captured.value.code == "SOURCE_MONTH_MISMATCH"
    assert raw_count == 0
    assert batch == ("failed", "SOURCE_MONTH_MISMATCH")
