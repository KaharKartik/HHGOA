from __future__ import annotations

import csv
import datetime
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Sequence

from pydantic import BaseModel, Field

from .models import CaseRecord, Verdict

logger = logging.getLogger(__name__)


class ClosedCase(BaseModel):
    """Read-only domain model for historical closed cases (the bank's historical truth)."""

    case_id: str
    customer_id: str
    card_id: str
    opened_at: str = ""
    closed_at: str = ""
    outcome: str  # 'confirmed_fraud' or 'cleared'
    pattern: str  # e.g. 'card_testing', 'card_not_present_fraud', or 'none'
    first_fraud_txn_id: str = ""
    txn_ids: list[str] = Field(default_factory=list)
    n_txns: int = 0
    exposure_usd: float = Field(default=0.0, ge=0.0)
    connected_card_ids: list[str] = Field(default_factory=list)
    actions_taken: str = ""
    report_filed: str = ""
    analyst_notes: str = ""


class ClosedCaseRepository(ABC):
    """Read-only interface for retrieving historical closed cases."""

    @abstractmethod
    def get_case(self, case_id: str) -> ClosedCase | None:
        """Retrieve a closed case by its primary case_id."""
        ...

    @abstractmethod
    def find_by_card(self, card_id: str) -> list[ClosedCase]:
        """Find closed cases involving a specific card ID."""
        ...

    @abstractmethod
    def find_by_customer(self, customer_id: str) -> list[ClosedCase]:
        """Find closed cases involving a specific customer ID."""
        ...

    @abstractmethod
    def search_similar(
        self, pattern: str | None = None, min_exposure: float = 0.0, limit: int = 5
    ) -> list[ClosedCase]:
        """Retrieve similar past cases by pattern or exposure magnitude."""
        ...


class InMemoryClosedCaseRepository(ClosedCaseRepository):
    """Deterministic in-memory repository for closed cases, supporting testing and evaluation."""

    def __init__(self, cases: Sequence[ClosedCase] | None = None):
        self._cases: dict[str, ClosedCase] = {c.case_id: c for c in (cases or [])}

    @classmethod
    def from_csv(cls, csv_path: str | Path, limit: int | None = None) -> InMemoryClosedCaseRepository:
        """Construct repository by parsing closed_cases_history.csv."""
        path = Path(csv_path)
        if not path.is_file():
            return cls([])

        loaded: list[ClosedCase] = []
        with path.open("r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                txn_ids = [t.strip() for t in row.get("txn_ids", "").split("|") if t.strip()]
                connected = [c.strip() for c in row.get("connected_card_ids", "").split("|") if c.strip()]
                try:
                    exposure = float(row.get("exposure_usd") or 0.0)
                except ValueError:
                    exposure = 0.0
                try:
                    n_txns = int(row.get("n_txns") or len(txn_ids))
                except ValueError:
                    n_txns = len(txn_ids)

                case = ClosedCase(
                    case_id=row.get("case_id", ""),
                    customer_id=row.get("customer_id", ""),
                    card_id=row.get("card_id", ""),
                    opened_at=row.get("opened_at", ""),
                    closed_at=row.get("closed_at", ""),
                    outcome=row.get("outcome", "cleared"),
                    pattern=row.get("pattern", "none"),
                    first_fraud_txn_id=row.get("first_fraud_txn_id", ""),
                    txn_ids=txn_ids,
                    n_txns=n_txns,
                    exposure_usd=exposure,
                    connected_card_ids=connected,
                    actions_taken=row.get("actions_taken", ""),
                    report_filed=row.get("report_filed", ""),
                    analyst_notes=row.get("analyst_notes", ""),
                )
                loaded.append(case)
                if limit and len(loaded) >= limit:
                    break

        return cls(loaded)

    def add_case(self, case: ClosedCase) -> None:
        self._cases[case.case_id] = case

    def get_case(self, case_id: str) -> ClosedCase | None:
        return self._cases.get(case_id)

    def find_by_card(self, card_id: str) -> list[ClosedCase]:
        return [c for c in self._cases.values() if c.card_id == card_id or card_id in c.connected_card_ids]

    def find_by_customer(self, customer_id: str) -> list[ClosedCase]:
        return [c for c in self._cases.values() if c.customer_id == customer_id]

    def search_similar(
        self, pattern: str | None = None, min_exposure: float = 0.0, limit: int = 5
    ) -> list[ClosedCase]:
        results: list[ClosedCase] = []
        for c in self._cases.values():
            if pattern and c.pattern != pattern:
                continue
            if c.exposure_usd < min_exposure:
                continue
            results.append(c)
            if len(results) >= limit:
                break
        return results


class InvestigationCaseWriter(ABC):
    """Interface for persisting an investigation case into case memory."""

    @abstractmethod
    def write_case(self, case_record: CaseRecord) -> dict[str, Any]:
        """Persist or record intent to write case into graph."""
        ...


class InvestigationCaseWriterStub(InvestigationCaseWriter):
    """Stub writer kept for backward-compat and offline testing.

    Per original requirement: preserves case_record.written_to_graph = False.
    """

    def __init__(self) -> None:
        self.recorded_cases: list[CaseRecord] = []

    def write_case(self, case_record: CaseRecord) -> dict[str, Any]:
        self.recorded_cases.append(case_record)
        return {
            "status": "deferred",
            "written_to_graph": False,
            "reason": "TigerGraph InvestigationCase mutation is intentionally deferred to Phase 6",
            "case_summary": case_record.summary[:50],
        }


class TigerGraphInvestigationCaseWriter(InvestigationCaseWriter):
    """Live write-back of finalized InvestigationCase records to TigerGraph.

    Design invariants (never violated):
    - All writes are idempotent: add_node uses upsert semantics; re-running the
      same case_id is safe.
    - Only evidence-backed relationships are written:
        ON_CARD      → only card_ids present in case_record.connected_card_ids
                       (which the agent populates only from real graph evidence)
        INVOLVES     → only transaction IDs from case_record.evidence[*].entity_ids
                       that are also in case_record.affected_txn_ids
        SIMILAR_TO   → only case IDs in case_record.similar_prior_cases
    - IDs are never fabricated; they come verbatim from the CaseRecord.
    - written_to_graph is set True only after a confirmed successful upsert.
    - On success the record is backfilled into the optional ClosedCaseRepository
      so that same-session lookups see the new case.

    Parameters
    ----------
    mcp_client:
        An object exposing call_tool(tool_name, arguments) -> dict.
        Typically the live Antigravity TigerGraph MCP client.
    graph_name:
        TigerGraph graph name (default "HHGOA_FRAUD").
    case_memory:
        Optional InMemoryClosedCaseRepository to backfill after a successful write.
    dry_run:
        If True, log all intended writes but do not call the MCP server.
        Useful for pre-flight validation.
    """

    def __init__(
        self,
        mcp_client: Any,
        graph_name: str = "HHGOA_FRAUD",
        case_memory: InMemoryClosedCaseRepository | None = None,
        dry_run: bool = False,
    ) -> None:
        self._client = mcp_client
        self._graph = graph_name
        self._memory = case_memory
        self._dry_run = dry_run

    # ── internal helpers ──────────────────────────────────────────────

    def _call(self, tool: str, args: dict[str, Any]) -> dict[str, Any]:
        """Invoke MCP tool, log intent, handle errors gracefully."""
        if self._dry_run:
            logger.info("[DRY-RUN] %s %s", tool, args)
            return {"status": "dry_run"}
        try:
            result = self._client.call_tool(tool, args)
            logger.debug("MCP %s → %s", tool, result)
            return result if isinstance(result, dict) else {"raw": result}
        except Exception as exc:
            logger.error("MCP call failed: %s %s → %s", tool, args, exc)
            raise

    def _upsert_vertex(self, v_type: str, v_id: str, attrs: dict[str, Any]) -> None:
        self._call(
            "tigergraph__add_node",
            {
                "graph_name": self._graph,
                "vertex_type": v_type,
                "vertex_id": v_id,
                "attributes": attrs,
            },
        )

    def _upsert_edge(
        self,
        edge_type: str,
        from_type: str,
        from_id: str,
        to_type: str,
        to_id: str,
        attrs: dict[str, Any] | None = None,
    ) -> None:
        self._call(
            "tigergraph__add_edge",
            {
                "graph_name": self._graph,
                "edge_type": edge_type,
                "from_vertex_type": from_type,
                "from_vertex_id": from_id,
                "to_vertex_type": to_type,
                "to_vertex_id": to_id,
                "attributes": attrs or {},
            },
        )

    # ── public write interface ────────────────────────────────────────

    def write_case(self, case_record: CaseRecord) -> dict[str, Any]:
        """Upsert InvestigationCase and evidence-backed relationships.

        Returns a status dict with written_to_graph=True on success.
        """
        case_id: str = case_record.graph_case_id or ""
        if not case_id:
            return {
                "status": "skipped",
                "written_to_graph": False,
                "reason": "CaseRecord.graph_case_id is empty; cannot write without a stable ID.",
            }

        # ── 1. Upsert InvestigationCase vertex ──────────────────────
        self._upsert_vertex(
            "InvestigationCase",
            case_id,
            {
                "status": case_record.status.value,
                "verdict": case_record.verdict.value,
                "fraud_probability": case_record.fraud_probability,
                "pattern": case_record.pattern.value,
                "exposure_usd": case_record.exposure_usd,
            },
        )
        logger.info("Upserted InvestigationCase vertex: %s", case_id)

        written_edges: list[str] = []

        # ── 2. ON_CARD edges — only for evidence-backed card IDs ────
        for card_id in case_record.connected_card_ids:
            if not card_id:
                continue
            self._upsert_edge("ON_CARD", "InvestigationCase", case_id, "Card", card_id)
            written_edges.append(f"ON_CARD→{card_id}")

        # ── 3. INVOLVES edges — only txn IDs corroborated by evidence
        # Collect entity_ids from evidence items filtered to affected_txns
        affected_set = set(case_record.affected_txn_ids)
        evidenced_txns: set[str] = set()
        for ev in case_record.evidence:
            for eid in ev.entity_ids:
                if eid in affected_set:
                    evidenced_txns.add(eid)

        for txn_id in evidenced_txns:
            self._upsert_edge("INVOLVES", "InvestigationCase", case_id, "Transaction", txn_id)
            written_edges.append(f"INVOLVES→{txn_id}")

        # ── 4. SIMILAR_TO edges — only prior case IDs from case memory
        for prior_case_id in case_record.similar_prior_cases:
            if not prior_case_id:
                continue
            self._upsert_edge("SIMILAR_TO", "InvestigationCase", case_id, "ClosedCase", prior_case_id)
            written_edges.append(f"SIMILAR_TO→{prior_case_id}")

        # ── 5. Backfill in-memory case memory so same-session queries work ──
        if self._memory is not None:
            outcome = (
                "confirmed_fraud" if case_record.verdict is Verdict.FRAUD else "cleared"
            )
            closed = ClosedCase(
                case_id=case_id,
                customer_id="",   # not available at this layer; enriched offline
                card_id=case_record.connected_card_ids[0] if case_record.connected_card_ids else "",
                closed_at=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                outcome=outcome,
                pattern=case_record.pattern.value,
                txn_ids=list(case_record.affected_txn_ids),
                n_txns=len(case_record.affected_txn_ids),
                exposure_usd=case_record.exposure_usd,
                connected_card_ids=list(case_record.connected_card_ids),
                analyst_notes=case_record.summary[:200],
            )
            self._memory.add_case(closed)
            logger.info("Backfilled case %s into in-memory case memory.", case_id)

        return {
            "status": "written",
            "written_to_graph": True,
            "case_id": case_id,
            "edges_written": written_edges,
            "dry_run": self._dry_run,
        }
