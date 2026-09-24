"""Data foundation: source discovery, validation, and typed record loading."""

from .loader import DataLoader, DatasetHandle
from .validator import validate_data

__all__ = ["DataLoader", "DatasetHandle", "validate_data"]
