from __future__ import annotations

import csv
from pathlib import Path
from zipfile import ZipFile

import pytest

from flightops.ingestion.errors import IngestionError
from flightops.ingestion.schema import SOURCE_COLUMNS
from flightops.ingestion.source import discover_inputs, prepare_source
from flightops.ingestion.validation import inspect_source


def write_csv(
    path: Path,
    *,
    periods: list[tuple[int, int]] | None = None,
    trailing_empty: bool = True,
) -> bytes:
    periods = periods or [(2024, 1)]
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow([*SOURCE_COLUMNS, ""] if trailing_empty else SOURCE_COLUMNS)
        for year, month in periods:
            row = [""] * len(SOURCE_COLUMNS)
            row[SOURCE_COLUMNS.index("Year")] = str(year)
            row[SOURCE_COLUMNS.index("Month")] = str(month)
            row[SOURCE_COLUMNS.index("FlightDate")] = f"{year}-{month:02d}-01"
            writer.writerow([*row, ""] if trailing_empty else row)
    return path.read_bytes()


def test_csv_and_zip_share_decompressed_csv_checksum(tmp_path: Path) -> None:
    csv_path = tmp_path / "month.csv"
    csv_bytes = write_csv(csv_path, periods=[(2024, 1), (2024, 1)])
    zip_path = tmp_path / "month.zip"
    with ZipFile(zip_path, "w") as archive:
        archive.writestr("nested/month.csv", csv_bytes)
        archive.writestr("readme.html", "metadata")

    csv_profile = inspect_source(prepare_source(csv_path))
    zip_profile = inspect_source(prepare_source(zip_path))

    assert csv_profile.csv_sha256 == zip_profile.csv_sha256
    assert csv_profile.row_count == zip_profile.row_count == 2
    assert csv_profile.has_empty_trailing_column is True


def test_discovery_is_recursive_filtered_and_deterministic(tmp_path: Path) -> None:
    nested = tmp_path / "nested"
    nested.mkdir()
    write_csv(nested / "b.csv")
    write_csv(tmp_path / "a.csv")
    (tmp_path / "readme.html").write_text("ignored")

    found = discover_inputs([tmp_path])

    assert [path.name for path in found] == ["a.csv", "b.csv"]


def test_mixed_month_file_fails_with_data_row(tmp_path: Path) -> None:
    path = tmp_path / "mixed.csv"
    write_csv(path, periods=[(2024, 1), (2024, 2)])

    with pytest.raises(IngestionError) as captured:
        inspect_source(prepare_source(path))

    assert captured.value.code == "SOURCE_MONTH_MISMATCH"
    assert captured.value.row_number == 2


def test_unknown_column_is_schema_mismatch(tmp_path: Path) -> None:
    path = tmp_path / "unknown.csv"
    with path.open("w", newline="", encoding="utf-8") as stream:
        csv.writer(stream).writerow([*SOURCE_COLUMNS, "NewField"])

    with pytest.raises(IngestionError) as captured:
        inspect_source(prepare_source(path))

    assert captured.value.code == "SCHEMA_MISMATCH"


def test_nonempty_trailing_column_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "trailing.csv"
    write_csv(path)
    lines = path.read_text().splitlines()
    lines[1] += "unexpected"
    path.write_text("\n".join(lines) + "\n")

    with pytest.raises(IngestionError) as captured:
        inspect_source(prepare_source(path))

    assert captured.value.code == "NONEMPTY_TRAILING_COLUMN"


def test_zip_path_traversal_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "unsafe.zip"
    with ZipFile(path, "w") as archive:
        archive.writestr("../month.csv", b"data")

    with pytest.raises(IngestionError) as captured:
        prepare_source(path)

    assert captured.value.code == "UNSAFE_ZIP_MEMBER"


def test_zip_requires_exactly_one_csv(tmp_path: Path) -> None:
    path = tmp_path / "ambiguous.zip"
    with ZipFile(path, "w") as archive:
        archive.writestr("one.csv", b"one")
        archive.writestr("two.csv", b"two")

    with pytest.raises(IngestionError) as captured:
        prepare_source(path)

    assert captured.value.code == "CSV_MEMBER_COUNT"
