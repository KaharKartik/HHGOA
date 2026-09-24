from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.data.loader import DataLoader
from app.data.schemas import EXPECTED_COLUMNS
from app.data.validator import validate_data


def _row(filename: str, **values: str) -> dict[str, str]:
    row = {column: "" for column in EXPECTED_COLUMNS[filename]}
    row.update(values)
    return row


def _write(directory: Path, filename: str, rows: list[dict[str, str]]) -> None:
    with (directory / filename).open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=EXPECTED_COLUMNS[filename])
        writer.writeheader()
        writer.writerows(rows)


import shutil
import uuid

@pytest.fixture
def raw_dir() -> Iterator[Path]:
    scratch = ROOT / "scratch" / f"raw_dir_{uuid.uuid4().hex}"
    scratch.mkdir(parents=True, exist_ok=True)
    _write(scratch, "transactions.csv", [_row("transactions.csv", TransactionID="1", TransactionDT="10", TransactionAmt="12.50", customer_id="C1", ts="2016-07-02 00:00:00", risk_score="0.25")])
    _write(scratch, "identity.csv", [_row("identity.csv", TransactionID="1")])
    _write(scratch, "case_pack.csv", [_row("case_pack.csv", case_id="HHG-001", opened_at="2016-07-02 00:00:00", trigger_type="test", trigger_text="test", flagged_txn_id="1", card_id="C1-K1", customer_id="C1", risk_score="0.25")])
    _write(scratch, "closed_cases_history.csv", [_row("closed_cases_history.csv", case_id="CC-001", customer_id="C1", card_id="C1-K1", opened_at="2016-07-02 00:00:00", closed_at="2016-07-03 00:00:00", outcome="cleared", pattern="none", txn_ids="1", n_txns="1", exposure_usd="0.0", actions_taken="CLOSE", report_filed="No", analyst_notes="test")])
    try:
        yield scratch
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_successful_loading_preserves_raw_values(raw_dir: Path) -> None:
    loader = DataLoader(raw_dir)
    handle = loader.dataset("transactions.csv")
    it = handle.iter_records()
    record = next(it)
    it.close()
    assert record.TransactionID == 1
    assert record.TransactionAmt == 12.5
    assert record.raw_values["TransactionAmt"] == "12.50"


def test_missing_file_fails(raw_dir: Path) -> None:
    (raw_dir / "identity.csv").unlink()
    report = validate_data(raw_dir)
    assert not report.valid
    assert "required file missing: identity.csv" in report.errors


def test_missing_column_fails(raw_dir: Path) -> None:
    path = raw_dir / "transactions.csv"
    lines = path.read_text(encoding="utf-8").splitlines()
    columns = lines[0].split(",")
    index = columns.index("ts")
    lines[0] = ",".join(column for column in columns if column != "ts")
    lines[1] = ",".join(value for number, value in enumerate(lines[1].split(",")) if number != index)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert any("required columns" in error for error in validate_data(raw_dir).errors)


def test_invalid_timestamp_fails(raw_dir: Path) -> None:
    path = raw_dir / "transactions.csv"
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    rows[0]["ts"] = "not-a-timestamp"
    _write(raw_dir, "transactions.csv", rows)
    assert any("invalid timestamp" in error for error in validate_data(raw_dir).errors)


def test_invalid_numeric_fails(raw_dir: Path) -> None:
    path = raw_dir / "transactions.csv"
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    rows[0]["TransactionAmt"] = "not-a-number"
    _write(raw_dir, "transactions.csv", rows)
    assert any("invalid numeric" in error for error in validate_data(raw_dir).errors)


def test_duplicate_key_fails(raw_dir: Path) -> None:
    path = raw_dir / "transactions.csv"
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    rows.append(rows[0])
    _write(raw_dir, "transactions.csv", rows)
    assert any("identifier TransactionID has 1 duplicate" in error for error in validate_data(raw_dir).errors)


def test_relationship_validation_fails(raw_dir: Path) -> None:
    path = raw_dir / "case_pack.csv"
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    rows[0]["flagged_txn_id"] = "999"
    _write(raw_dir, "case_pack.csv", rows)
    assert any("case_pack.csv.flagged_txn_id" in error for error in validate_data(raw_dir).errors)

