"""Tests for TigerGraphInvestigationCaseWriter.

Covers:
- Dry-run mode: no MCP calls, returns dry_run=True
- Upsert idempotency: re-running same case_id is safe (only MCP behaviour)
- Evidence-filtered edges: ON_CARD, INVOLVES, SIMILAR_TO written only from
  real CaseRecord evidence — no fabricated IDs
- Missing graph_case_id: skipped gracefully
- Case-memory backfill: InMemoryClosedCaseRepository gets the new record
- MCP failure: exception propagated cleanly (no silent swallow)
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.investigation.case_memory import (
    InMemoryClosedCaseRepository,
    TigerGraphInvestigationCaseWriter,
)
from app.investigation.models import (
    CaseRecord,
    CaseStatus,
    EvidenceItem,
    EvidenceSource,
    Pattern,
    Verdict,
)


# ── fixtures ──────────────────────────────────────────────────────────────────

def _fraud_case(
    graph_case_id: str = "IC-TEST-001",
    connected_cards: list[str] | None = None,
    affected_txns: list[str] | None = None,
    evidence_txns: list[str] | None = None,
    similar_cases: list[str] | None = None,
) -> CaseRecord:
    """Build a minimal FRAUD CaseRecord for writer tests."""
    cards = connected_cards or ["CARD-A", "CARD-B"]
    txns = affected_txns or ["T1", "T2"]
    ev_txns = evidence_txns or txns  # default: evidence references same txns
    sim = similar_cases or ["CC-PRIOR-1"]

    return CaseRecord(
        status=CaseStatus.CLOSED_FRAUD,
        verdict=Verdict.FRAUD,
        fraud_probability=0.95,
        pattern=Pattern.CARD_TESTING,
        affected_txn_ids=txns,
        first_suspicious_txn_id=txns[0] if txns else "",
        connected_card_ids=cards,
        connected_device_profiles=[],
        exposure_usd=500.0,
        evidence=[
            EvidenceItem(
                claim="Card testing sequence observed",
                source=EvidenceSource.GRAPH,
                ref="transaction_sequence",
                entity_ids=ev_txns,
            )
        ],
        similar_prior_cases=sim,
        summary="Automated card testing fraud confirmed.",
        written_to_graph=False,
        graph_case_id=graph_case_id,
    )


def _legit_case() -> CaseRecord:
    return CaseRecord(
        status=CaseStatus.CLOSED_LEGITIMATE,
        verdict=Verdict.LEGITIMATE,
        fraud_probability=0.05,
        pattern=Pattern.NONE,
        affected_txn_ids=[],
        first_suspicious_txn_id="",
        connected_card_ids=[],
        connected_device_profiles=[],
        exposure_usd=0.0,
        evidence=[
            EvidenceItem(
                claim="Customer confirmed transaction",
                source=EvidenceSource.CUSTOMER,
                ref="customer_response",
                entity_ids=["T-LEGIT"],
            )
        ],
        similar_prior_cases=[],
        summary="Transaction confirmed legitimate by customer.",
        written_to_graph=False,
        graph_case_id="IC-LEGIT-001",
    )


# ── dry-run mode ──────────────────────────────────────────────────────────────

def test_dry_run_no_mcp_calls():
    """In dry-run mode, no MCP calls are made and result flags dry_run=True."""
    fake_client = MagicMock()
    writer = TigerGraphInvestigationCaseWriter(
        mcp_client=fake_client, dry_run=True
    )
    result = writer.write_case(_fraud_case())

    fake_client.call_tool.assert_not_called()
    assert result["written_to_graph"] is True
    assert result["dry_run"] is True
    assert result["case_id"] == "IC-TEST-001"


# ── vertex + edge writes ──────────────────────────────────────────────────────

def test_upserts_investigation_case_vertex():
    """Writer calls add_node for the InvestigationCase vertex."""
    fake_client = MagicMock()
    fake_client.call_tool.return_value = {"status": "ok"}

    writer = TigerGraphInvestigationCaseWriter(mcp_client=fake_client)
    writer.write_case(_fraud_case(graph_case_id="IC-VERTEX-1"))

    node_calls = [
        c for c in fake_client.call_tool.call_args_list
        if c[0][0] == "tigergraph__add_node"
    ]
    assert len(node_calls) == 1
    args = node_calls[0][0][1]
    assert args["vertex_type"] == "InvestigationCase"
    assert args["vertex_id"] == "IC-VERTEX-1"
    assert args["attributes"]["verdict"] == "fraud"
    assert args["attributes"]["status"] == "closed_fraud"
    assert args["attributes"]["fraud_probability"] == 0.95


def test_writes_on_card_edges_for_connected_cards():
    """ON_CARD edges are written for each connected_card_id."""
    fake_client = MagicMock()
    fake_client.call_tool.return_value = {"status": "ok"}

    writer = TigerGraphInvestigationCaseWriter(mcp_client=fake_client)
    writer.write_case(_fraud_case(connected_cards=["CARD-X", "CARD-Y"]))

    edge_calls = [
        c[0][1] for c in fake_client.call_tool.call_args_list
        if c[0][0] == "tigergraph__add_edge"
    ]
    on_card_targets = {e["to_vertex_id"] for e in edge_calls if e["edge_type"] == "ON_CARD"}
    assert "CARD-X" in on_card_targets
    assert "CARD-Y" in on_card_targets


def test_writes_involves_edges_for_evidenced_txns():
    """INVOLVES edges are written only for txns present in both affected_txn_ids and evidence entity_ids."""
    fake_client = MagicMock()
    fake_client.call_tool.return_value = {"status": "ok"}

    writer = TigerGraphInvestigationCaseWriter(mcp_client=fake_client)
    # evidence references T1 only; T2 is in affected_txns but not in evidence
    writer.write_case(
        _fraud_case(affected_txns=["T1", "T2"], evidence_txns=["T1"])
    )

    edge_calls = [
        c[0][1] for c in fake_client.call_tool.call_args_list
        if c[0][0] == "tigergraph__add_edge"
    ]
    involves_targets = {e["to_vertex_id"] for e in edge_calls if e["edge_type"] == "INVOLVES"}
    assert "T1" in involves_targets
    assert "T2" not in involves_targets, "T2 not in evidence — must not be written"


def test_writes_similar_to_edges_for_prior_cases():
    """SIMILAR_TO edges written for each similar_prior_cases entry."""
    fake_client = MagicMock()
    fake_client.call_tool.return_value = {"status": "ok"}

    writer = TigerGraphInvestigationCaseWriter(mcp_client=fake_client)
    writer.write_case(_fraud_case(similar_cases=["CC-OLD-1", "CC-OLD-2"]))

    edge_calls = [
        c[0][1] for c in fake_client.call_tool.call_args_list
        if c[0][0] == "tigergraph__add_edge"
    ]
    sim_targets = {e["to_vertex_id"] for e in edge_calls if e["edge_type"] == "SIMILAR_TO"}
    assert "CC-OLD-1" in sim_targets
    assert "CC-OLD-2" in sim_targets


# ── no-fabrication invariant ──────────────────────────────────────────────────

def test_no_fabricated_ids_in_edges():
    """Every edge target ID must come verbatim from the CaseRecord — no fabricated IDs."""
    fake_client = MagicMock()
    fake_client.call_tool.return_value = {"status": "ok"}

    case = _fraud_case(
        connected_cards=["CARD-REAL"],
        affected_txns=["TXN-REAL"],
        evidence_txns=["TXN-REAL"],
        similar_cases=["PRIOR-REAL"],
    )
    writer = TigerGraphInvestigationCaseWriter(mcp_client=fake_client)
    result = writer.write_case(case)

    allowed_ids = {"CARD-REAL", "TXN-REAL", "PRIOR-REAL", "IC-TEST-001"}
    edge_calls = [
        c[0][1] for c in fake_client.call_tool.call_args_list
        if c[0][0] == "tigergraph__add_edge"
    ]
    for ec in edge_calls:
        assert ec["to_vertex_id"] in allowed_ids, (
            f"Fabricated ID detected in edge: {ec}"
        )


# ── missing graph_case_id guard ───────────────────────────────────────────────

def test_skips_write_when_graph_case_id_empty():
    """When graph_case_id is empty, write is skipped and written_to_graph=False."""
    fake_client = MagicMock()
    writer = TigerGraphInvestigationCaseWriter(mcp_client=fake_client)

    case = _fraud_case(graph_case_id="")
    result = writer.write_case(case)

    fake_client.call_tool.assert_not_called()
    assert result["written_to_graph"] is False
    assert result["status"] == "skipped"


# ── case-memory backfill ──────────────────────────────────────────────────────

def test_backfills_case_memory_on_success():
    """After a successful write, the finalized case appears in InMemoryClosedCaseRepository."""
    fake_client = MagicMock()
    fake_client.call_tool.return_value = {"status": "ok"}

    memory = InMemoryClosedCaseRepository()
    writer = TigerGraphInvestigationCaseWriter(mcp_client=fake_client, case_memory=memory)

    writer.write_case(_fraud_case(graph_case_id="IC-MEM-001"))

    found = memory.get_case("IC-MEM-001")
    assert found is not None
    assert found.case_id == "IC-MEM-001"
    assert found.outcome == "confirmed_fraud"
    assert found.pattern == "card_testing"
    assert found.exposure_usd == 500.0


def test_backfill_legit_case_has_cleared_outcome():
    """Legitimate verdict writes 'cleared' outcome into case memory."""
    fake_client = MagicMock()
    fake_client.call_tool.return_value = {"status": "ok"}

    memory = InMemoryClosedCaseRepository()
    writer = TigerGraphInvestigationCaseWriter(mcp_client=fake_client, case_memory=memory)
    writer.write_case(_legit_case())

    found = memory.get_case("IC-LEGIT-001")
    assert found is not None
    assert found.outcome == "cleared"


def test_no_backfill_when_memory_not_injected():
    """When case_memory=None, no AttributeError is raised — backfill is skipped."""
    fake_client = MagicMock()
    fake_client.call_tool.return_value = {"status": "ok"}

    writer = TigerGraphInvestigationCaseWriter(mcp_client=fake_client, case_memory=None)
    result = writer.write_case(_fraud_case())
    assert result["written_to_graph"] is True  # write succeeded, backfill silently skipped


# ── MCP failure propagation ───────────────────────────────────────────────────

def test_mcp_failure_propagates_exception():
    """If the MCP client raises, the writer does not silently swallow it."""
    fake_client = MagicMock()
    fake_client.call_tool.side_effect = RuntimeError("MCP server unavailable")

    writer = TigerGraphInvestigationCaseWriter(mcp_client=fake_client)
    with pytest.raises(RuntimeError, match="MCP server unavailable"):
        writer.write_case(_fraud_case())


# ── result structure ──────────────────────────────────────────────────────────

def test_result_structure_on_success():
    """Successful write result contains expected keys."""
    fake_client = MagicMock()
    fake_client.call_tool.return_value = {"status": "ok"}

    writer = TigerGraphInvestigationCaseWriter(mcp_client=fake_client)
    result = writer.write_case(_fraud_case())

    assert result["status"] == "written"
    assert result["written_to_graph"] is True
    assert "case_id" in result
    assert isinstance(result["edges_written"], list)
    assert result["dry_run"] is False
