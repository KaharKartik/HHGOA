"""Dataset contracts generated strictly from the supplied CSV headers."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, create_model


class ValueKind(str, Enum):
    INTEGER = "integer"
    NUMBER = "number"
    TEXT = "text"


class RawRecord(BaseModel):
    """Base for source rows. ``raw_values`` retains the original CSV strings."""

    model_config = ConfigDict(extra="forbid")
    raw_values: dict[str, str | None]


# These contracts are the exact current raw headers. Ranges mirror the actual
# numbered source columns and do not imply business semantics.
TRANSACTION_COLUMNS = (
    ["TransactionID", "TransactionDT", "TransactionAmt", "ProductCD"]
    + [f"card{i}" for i in range(1, 7)]
    + ["addr1", "addr2", "dist1", "dist2", "P_emaildomain", "R_emaildomain"]
    + [f"C{i}" for i in range(1, 15)]
    + [f"D{i}" for i in range(1, 16)]
    + [f"M{i}" for i in range(1, 10)]
    + [f"V{i}" for i in range(1, 340)]
    + ["customer_id", "ts", "channel", "risk_score"]
)
IDENTITY_COLUMNS = ["TransactionID"] + [f"id_{i:02d}" for i in range(1, 39)] + ["DeviceType", "DeviceInfo"]
CASE_PACK_COLUMNS = ["case_id", "opened_at", "trigger_type", "trigger_text", "flagged_txn_id", "card_id", "customer_id", "risk_score"]
CLOSED_CASE_COLUMNS = ["case_id", "customer_id", "card_id", "opened_at", "closed_at", "outcome", "pattern", "first_fraud_txn_id", "txn_ids", "n_txns", "exposure_usd", "connected_card_ids", "actions_taken", "report_filed", "analyst_notes"]
PROCESSED_COLUMNS = ["TransactionID", "TransactionAmt", "ProductCD", "card1", "card4", "card6", "addr1", "addr2", "dist1", "dist2", "P_emaildomain", "R_emaildomain", "customer_id", "ts", "channel", "risk_score", "id_15", "id_23", "id_30", "id_31", "id_33", "id_34", "DeviceType", "DeviceInfo"]

EXPECTED_COLUMNS: dict[str, list[str]] = {
    "transactions.csv": TRANSACTION_COLUMNS,
    "identity.csv": IDENTITY_COLUMNS,
    "case_pack.csv": CASE_PACK_COLUMNS,
    "closed_cases_history.csv": CLOSED_CASE_COLUMNS,
    "pack_and_ring_txns.csv": PROCESSED_COLUMNS,
}


def pydantic_record_model(dataset_name: str, kinds: dict[str, ValueKind]) -> type[RawRecord]:
    """Build a strict typed model containing only headers from the supplied dataset."""

    python_types: dict[ValueKind, Any] = {
        ValueKind.INTEGER: int | None,
        ValueKind.NUMBER: float | None,
        ValueKind.TEXT: str | None,
    }
    fields = {name: (python_types[kind], None) for name, kind in kinds.items()}
    return create_model(f"{dataset_name.replace('.', '_').title()}Record", __base__=RawRecord, **fields)
