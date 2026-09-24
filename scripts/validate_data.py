"""Validate the supplied raw HHGOA data foundation."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.data.validator import validate_data  # noqa: E402


def main() -> int:
    # Windows consoles can default to CP1252, which cannot render the report's
    # checkmark. This affects presentation only; force UTF-8 for CLI output.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    report = validate_data(ROOT / "data" / "raw")
    print("## DATA VALIDATION\n")
    for filename, dataset in report.datasets.items():
        state = "✓" if not any(filename in error for error in report.errors) else "✗"
        print(f"{state} {filename}: {dataset.row_count:,} rows, {len(dataset.columns)} columns, {dataset.duplicate_rows:,} duplicate rows")
    print("\nSchemas (kind | nulls | estimated distinct values):")
    for filename, dataset in report.datasets.items():
        print(f"- {filename}")
        for column in dataset.columns:
            profile = dataset.column_profiles[column]
            timestamp = f" | {profile.timestamp_min} to {profile.timestamp_max}" if profile.timestamp_min else ""
            print(f"  {column}: {profile.kind.value} | {profile.null_count:,} ({profile.null_percentage(dataset.row_count):.2f}%) | ~{profile.unique_count_estimate:,}{timestamp}")
    print("\nRelationships:")
    for relation in report.relationships:
        print(f"- {relation.source}.{relation.source_column} -> {relation.target}.{relation.target_column}: {relation.matched_values:,}/{relation.checked_values:,} matched")
    print("\nResult: " + ("PASS" if report.valid else "FAIL"))
    if report.errors:
        print("\nErrors:")
        for error in report.errors:
            print(f"- {error}")
    return 0 if report.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
