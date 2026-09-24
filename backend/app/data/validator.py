"""Streaming discovery and validation for the actual HHGOA CSV inputs."""

from __future__ import annotations

import csv
import math
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .schemas import EXPECTED_COLUMNS, ValueKind


RAW_DATASETS = ("transactions.csv", "identity.csv", "case_pack.csv", "closed_cases_history.csv")
TIMESTAMP_COLUMNS = {"case_pack.csv": ("opened_at",), "closed_cases_history.csv": ("opened_at", "closed_at"), "transactions.csv": ("ts",)}
IDENTIFIER_COLUMNS = {"transactions.csv": ("TransactionID",), "identity.csv": ("TransactionID",), "case_pack.csv": ("case_id", "flagged_txn_id"), "closed_cases_history.csv": ("case_id",), "pack_and_ring_txns.csv": ("TransactionID",)}
RELATIONSHIP_COLUMNS = {"transactions.csv": ("TransactionID", "customer_id"), "identity.csv": ("TransactionID",), "case_pack.csv": ("flagged_txn_id", "customer_id"), "closed_cases_history.csv": ("customer_id", "first_fraud_txn_id"), "pack_and_ring_txns.csv": ("TransactionID", "customer_id")}
NUMERIC_COLUMNS = {"transactions.csv": ("TransactionID", "TransactionDT", "TransactionAmt", "risk_score"), "identity.csv": ("TransactionID",), "case_pack.csv": ("flagged_txn_id", "risk_score"), "closed_cases_history.csv": ("first_fraud_txn_id", "n_txns", "exposure_usd")}


@dataclass
class ColumnProfile:
    name: str
    kind: ValueKind
    null_count: int
    unique_count_estimate: int
    timestamp_min: str | None = None
    timestamp_max: str | None = None

    def null_percentage(self, row_count: int) -> float:
        return (self.null_count / row_count * 100) if row_count else 0.0


@dataclass
class DatasetProfile:
    filename: str
    row_count: int
    columns: tuple[str, ...]
    column_profiles: dict[str, ColumnProfile]
    duplicate_rows: int
    duplicate_identifiers: dict[str, int]

    @property
    def column_kinds(self) -> dict[str, ValueKind]:
        return {name: profile.kind for name, profile in self.column_profiles.items()}


@dataclass
class Relationship:
    source: str
    target: str
    source_column: str
    target_column: str
    checked_values: int
    matched_values: int


@dataclass
class ValidationReport:
    datasets: dict[str, DatasetProfile] = field(default_factory=dict)
    relationships: list[Relationship] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.errors

    def raise_for_errors(self) -> None:
        if self.errors:
            raise ValueError("Data validation failed: " + "; ".join(self.errors))


class _Hll:
    """Fixed-memory cardinality estimate for wide, large CSV discovery."""
    def __init__(self, precision: int = 10):
        self.precision = precision
        self.registers = [0] * (1 << precision)

    def add(self, value: str) -> None:
        # Python hashes are process-local but sufficient for an in-process
        # cardinality estimate and avoid a cryptographic hash per CSV cell.
        bits = hash(value) & ((1 << 64) - 1)
        index = bits >> (64 - self.precision)
        remainder = (bits << self.precision) & ((1 << 64) - 1)
        rank = (64 - remainder.bit_length() + 1) if remainder else 64 - self.precision + 1
        self.registers[index] = max(self.registers[index], rank)

    def estimate(self) -> int:
        count = len(self.registers)
        alpha = 0.7213 / (1 + 1.079 / count)
        estimate = alpha * count * count / sum(2.0 ** -item for item in self.registers)
        empty = self.registers.count(0)
        if empty and estimate <= 2.5 * count:
            estimate = count * math.log(count / empty)
        return round(estimate)


def _kind(value: str) -> ValueKind:
    try:
        int(value)
        return ValueKind.INTEGER
    except ValueError:
        try:
            float(value)
            return ValueKind.NUMBER
        except ValueError:
            return ValueKind.TEXT


def _combine(current: ValueKind | None, observed: ValueKind) -> ValueKind:
    if current is None:
        return observed
    if current is ValueKind.TEXT or observed is ValueKind.TEXT:
        return ValueKind.TEXT
    if current is ValueKind.NUMBER or observed is ValueKind.NUMBER:
        return ValueKind.NUMBER
    return ValueKind.INTEGER


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _profile_csv(path: Path, report: ValidationReport) -> tuple[DatasetProfile, dict[str, set[str]]]:
    filename = path.name
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        columns = tuple(reader.fieldnames or ())
        expected = EXPECTED_COLUMNS.get(filename)
        if expected is not None and list(columns) != expected:
            report.errors.append(f"{filename}: required columns do not match the supplied schema")
        nulls = Counter()
        kinds: dict[str, ValueKind | None] = {column: None for column in columns}
        cardinalities = {column: _Hll() for column in columns}
        timestamp_ranges: dict[str, list[datetime | None]] = {column: [None, None] for column in TIMESTAMP_COLUMNS.get(filename, ())}
        identifiers = {column: set() for column in RELATIONSHIP_COLUMNS.get(filename, ()) if column in columns}
        duplicate_identifiers = Counter()
        row_hashes: set[bytes] = set()
        duplicate_rows = 0
        row_count = 0
        for row_count, row in enumerate(reader, start=1):
            fingerprint = hash(tuple(row.get(column, "") or "" for column in columns))
            if fingerprint in row_hashes:
                duplicate_rows += 1
            else:
                row_hashes.add(fingerprint)
            for column in columns:
                value = row.get(column)
                if value in (None, ""):
                    nulls[column] += 1
                    continue
                kinds[column] = _combine(kinds[column], _kind(value))
                cardinalities[column].add(value)
                if column in identifiers:
                    if column in IDENTIFIER_COLUMNS.get(filename, ()) and value in identifiers[column]:
                        duplicate_identifiers[column] += 1
                    identifiers[column].add(value)
                if column in timestamp_ranges:
                    try:
                        parsed = _parse_timestamp(value)
                    except ValueError:
                        report.errors.append(f"{filename}: invalid timestamp in {column} at row {row_count}")
                    else:
                        lower, upper = timestamp_ranges[column]
                        timestamp_ranges[column] = [parsed if lower is None or parsed < lower else lower, parsed if upper is None or parsed > upper else upper]
                if column in NUMERIC_COLUMNS.get(filename, ()):
                    try:
                        float(value)
                    except ValueError:
                        report.errors.append(f"{filename}: invalid numeric value in {column} at row {row_count}")
        profiles = {
            column: ColumnProfile(column, kinds[column] or ValueKind.TEXT, nulls[column], cardinalities[column].estimate(), *(item.isoformat(sep=" ") if item else None for item in timestamp_ranges.get(column, [None, None])))
            for column in columns
        }
        for column in IDENTIFIER_COLUMNS.get(filename, ()):
            if column in columns and nulls[column]:
                report.errors.append(f"{filename}: critical identifier {column} has {nulls[column]} null value(s)")
            if duplicate_identifiers[column]:
                report.errors.append(f"{filename}: identifier {column} has {duplicate_identifiers[column]} duplicate value(s)")
        return DatasetProfile(filename, row_count, columns, profiles, duplicate_rows, dict(duplicate_identifiers)), identifiers


def _relationship(report: ValidationReport, source: str, source_column: str, source_values: Iterable[str], target: str, target_column: str, target_values: set[str]) -> None:
    values = [value for value in source_values if value]
    matched = sum(value in target_values for value in values)
    report.relationships.append(Relationship(source, target, source_column, target_column, len(values), matched))
    if matched != len(values):
        report.errors.append(f"{source}.{source_column}: {len(values) - matched} value(s) are missing from {target}.{target_column}")


def validate_data(raw_dir: Path | str, processed_dir: Path | str | None = None) -> ValidationReport:
    raw_dir = Path(raw_dir)
    report = ValidationReport()
    identifiers: dict[str, dict[str, set[str]]] = {}
    for filename in RAW_DATASETS:
        path = raw_dir / filename
        if not path.is_file():
            report.errors.append(f"required file missing: {filename}")
            continue
        profile, keys = _profile_csv(path, report)
        report.datasets[filename] = profile
        identifiers[filename] = keys
    processed = Path(processed_dir) if processed_dir is not None else raw_dir.parent / "processed"
    for path in sorted(processed.glob("*.csv")) if processed.is_dir() else []:
        profile, keys = _profile_csv(path, report)
        report.datasets[path.name] = profile
        identifiers[path.name] = keys
    if "transactions.csv" in identifiers:
        transaction_ids = identifiers["transactions.csv"].get("TransactionID", set())
        if "identity.csv" in identifiers:
            _relationship(report, "identity.csv", "TransactionID", identifiers["identity.csv"].get("TransactionID", set()), "transactions.csv", "TransactionID", transaction_ids)
        if "case_pack.csv" in identifiers:
            _relationship(report, "case_pack.csv", "flagged_txn_id", identifiers["case_pack.csv"].get("flagged_txn_id", set()), "transactions.csv", "TransactionID", transaction_ids)
        if "pack_and_ring_txns.csv" in identifiers:
            _relationship(report, "pack_and_ring_txns.csv", "TransactionID", identifiers["pack_and_ring_txns.csv"].get("TransactionID", set()), "transactions.csv", "TransactionID", transaction_ids)
        transaction_customers = identifiers["transactions.csv"].get("customer_id", set())
        for filename in ("case_pack.csv", "closed_cases_history.csv", "pack_and_ring_txns.csv"):
            if filename in identifiers:
                _relationship(report, filename, "customer_id", identifiers[filename].get("customer_id", set()), "transactions.csv", "customer_id", transaction_customers)
        if "closed_cases_history.csv" in identifiers:
            _relationship(report, "closed_cases_history.csv", "first_fraud_txn_id", identifiers["closed_cases_history.csv"].get("first_fraud_txn_id", set()), "transactions.csv", "TransactionID", transaction_ids)
    return report
