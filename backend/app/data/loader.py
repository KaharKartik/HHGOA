"""Reusable, streaming loader for validated CSV source datasets."""

from __future__ import annotations

import csv
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from .schemas import RawRecord, ValueKind, pydantic_record_model
from .validator import DatasetProfile, ValidationReport, validate_data


DEFAULT_RAW_DIR = Path(__file__).resolve().parents[3] / "data" / "raw"


@dataclass(frozen=True)
class DatasetHandle:
    name: str
    path: Path
    profile: DatasetProfile
    record_model: type[RawRecord]

    def iter_records(self) -> Iterator[RawRecord]:
        """Yield typed source records without materialising the dataset."""
        with self.path.open("r", encoding="utf-8-sig", newline="") as source:
            for row in csv.DictReader(source):
                raw = {key: (value if value != "" else None) for key, value in row.items()}
                values = {key: _coerce(value, self.profile.column_kinds[key]) for key, value in raw.items()}
                yield self.record_model.model_validate({**values, "raw_values": raw})


def _coerce(value: str | None, kind: ValueKind):
    if value is None:
        return None
    if kind is ValueKind.INTEGER:
        return int(value)
    if kind is ValueKind.NUMBER:
        return float(value)
    return value


class DataLoader:
    def __init__(self, raw_dir: Path | str = DEFAULT_RAW_DIR):
        self.raw_dir = Path(raw_dir)
        self._report: ValidationReport | None = None

    def validate(self) -> ValidationReport:
        self._report = validate_data(self.raw_dir)
        return self._report

    def dataset(self, filename: str) -> DatasetHandle:
        report = self._report or self.validate()
        report.raise_for_errors()
        profile = report.datasets[filename]
        return DatasetHandle(filename, self.raw_dir / filename, profile, pydantic_record_model(filename, profile.column_kinds))

    def datasets(self) -> Iterator[DatasetHandle]:
        report = self._report or self.validate()
        report.raise_for_errors()
        for filename in report.datasets:
            yield self.dataset(filename)
