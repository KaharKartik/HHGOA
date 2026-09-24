from __future__ import annotations

import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.investigation.case_memory import (
    ClosedCase,
    InMemoryClosedCaseRepository,
    InvestigationCaseWriterStub,
)
from app.investigation.models import (
    CaseRecord,
    CaseStatus,
    EvidenceItem,
    EvidenceSource,
    Pattern,
    Verdict,
)


def test_closed_case_model():
    case = ClosedCase(
        case_id="CC-001",
        customer_id="C100",
        card_id="C100-K1",
        opened_at="2016-08-01 10:00:00",
        closed_at="2016-08-02 12:00:00",
        outcome="confirmed_fraud",
        pattern="card_testing",
        first_fraud_txn_id="T1",
        txn_ids=["T1", "T2"],
        n_txns=2,
        exposure_usd=150.0,
        connected_card_ids=["C100-K2"],
        actions_taken="BLOCK_CARD",
        report_filed="Yes",
        analyst_notes="Card testing confirmed.",
    )
    assert case.case_id == "CC-001"
    assert case.exposure_usd == 150.0
    assert case.connected_card_ids == ["C100-K2"]


def test_in_memory_closed_case_repository():
    case1 = ClosedCase(
        case_id="CC-1",
        customer_id="C1",
        card_id="C1-K1",
        outcome="confirmed_fraud",
        pattern="card_testing",
        exposure_usd=300.0,
        connected_card_ids=["C1-K2"],
    )
    case2 = ClosedCase(
        case_id="CC-2",
        customer_id="C2",
        card_id="C2-K1",
        outcome="cleared",
        pattern="none",
        exposure_usd=0.0,
    )

    repo = InMemoryClosedCaseRepository([case1, case2])

    assert repo.get_case("CC-1") == case1
    assert repo.get_case("CC-99") is None

    # Card search includes primary card_id and connected_card_ids
    assert len(repo.find_by_card("C1-K1")) == 1
    assert len(repo.find_by_card("C1-K2")) == 1

    # Customer search
    assert len(repo.find_by_customer("C1")) == 1
    assert len(repo.find_by_customer("C99")) == 0

    # Pattern search
    testing_cases = repo.search_similar(pattern="card_testing")
    assert len(testing_cases) == 1
    assert testing_cases[0].case_id == "CC-1"


def test_investigation_case_writer_stub():
    writer = InvestigationCaseWriterStub()

    case_rec = CaseRecord(
        status=CaseStatus.CLOSED_FRAUD,
        verdict=Verdict.FRAUD,
        fraud_probability=0.95,
        pattern=Pattern.CARD_TESTING,
        affected_txn_ids=["T1"],
        first_suspicious_txn_id="T1",
        connected_card_ids=[],
        connected_device_profiles=[],
        exposure_usd=250.0,
        evidence=[
            EvidenceItem(
                claim="Fraudulent charge",
                source=EvidenceSource.GRAPH,
                ref="test",
                entity_ids=["T1"],
            )
        ],
        similar_prior_cases=[],
        summary="Test case summary",
        written_to_graph=False,
    )

    res = writer.write_case(case_rec)
    assert res["status"] == "deferred"
    assert res["written_to_graph"] is False
    assert len(writer.recorded_cases) == 1
    assert writer.recorded_cases[0].written_to_graph is False
