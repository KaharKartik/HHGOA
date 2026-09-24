from __future__ import annotations

import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.investigation.agent import InvestigationAgent
from app.investigation.case_memory import InMemoryClosedCaseRepository, InvestigationCaseWriterStub
from app.investigation.graph_rag import PolicyRetriever
from app.investigation.graph_service import MockGraphEvidenceService
from app.investigation.models import (
    Action,
    ActionRecommendation,
    ActionSet,
    ApprovalRoute,
    CaseStatus,
    EvidenceItem,
    EvidenceRequest,
    EvidenceRequestType,
    EvidenceSource,
    Pattern,
    SARRecord,
    Verdict,
)
from app.investigation.state import InvestigationState


def test_investigation_state_all_required_dimensions():
    """Verify InvestigationState supports all 13 required state dimensions."""
    state = InvestigationState(
        case_id="CASE-101",
        trigger_transaction={"TransactionID": "T1", "amount": 125.0},
        customer={"customer_id": "C100"},
        graph_evidence=[
            EvidenceItem(claim="Test graph claim", source=EvidenceSource.GRAPH, ref="q1", entity_ids=["T1"])
        ],
        policy_evidence=[],
        fraud_probability=0.85,
        uncertainty=0.15,
        pattern=Pattern.CARD_TESTING,
        evidence_requests=[
            EvidenceRequest(
                type=EvidenceRequestType.CUSTOMER_VALIDATION,
                asked_after_step=1,
                assumed_response="Simulated denial",
            )
        ],
        initial_recommendations=[
            ActionRecommendation(action=Action.VERIFY_WITH_CUSTOMER, route=ApprovalRoute.AUTO, reason="R1")
        ],
        final_recommendations=[
            ActionRecommendation(action=Action.BLOCK_CARD, route=ApprovalRoute.L1, reason="R2")
        ],
        sar_decision=SARRecord(file=False, reason="No trigger", total_amount_usd=0.0),
        next_best_action=ActionSet(initial=[], final=[], what_changed="none"),
        status=CaseStatus.OPEN,
        explanation="State dimensions validated.",
    )

    # Validate all 13 required dimensions are accessible and correctly typed
    assert state.case_id == "CASE-101"
    assert state.trigger_transaction["TransactionID"] == "T1"
    assert state.customer["customer_id"] == "C100"
    assert len(state.graph_evidence) == 1
    assert state.policy_evidence == []
    assert state.fraud_probability == 0.85
    assert state.uncertainty == 0.15
    assert state.pattern is Pattern.CARD_TESTING
    assert len(state.evidence_requests) == 1
    assert len(state.initial_recommendations) == 1
    assert len(state.final_recommendations) == 1
    assert state.sar_decision.file is False
    assert state.next_best_action is not None
    assert state.status is CaseStatus.OPEN
    assert state.explanation == "State dimensions validated."


def test_state_to_case_record_invariants():
    # Legitimate case must have 0 exposure and empty affected_txn_ids
    legit_state = InvestigationState(
        case_id="LEGIT-1",
        verdict=Verdict.LEGITIMATE,
        fraud_probability=0.05,
        pattern=Pattern.NONE,
        affected_txn_ids=["T1"],  # will be cleared by to_case_record
        exposure_usd=500.0,       # will be zeroed by to_case_record
    )
    rec = legit_state.to_case_record()
    assert rec.verdict is Verdict.LEGITIMATE
    assert rec.affected_txn_ids == []
    assert rec.exposure_usd == 0.0
    assert rec.written_to_graph is False


def test_agent_card_testing_investigation():
    """Agent detects card testing sequence, assesses fraud, applies R5, and recommends BLOCK_CARD."""
    graph_service = MockGraphEvidenceService()
    # Sequence of 3 micro transactions under $15 followed by a $150 charge
    seq = [
        {"transaction_id": "T0", "amount": 1.50},
        {"transaction_id": "T1", "amount": 2.00},
        {"transaction_id": "T2", "amount": 3.50},
        {"transaction_id": "T3", "amount": 150.00},
    ]
    graph_service.set_transaction_sequence("T0", seq)

    agent = InvestigationAgent(graph_service=graph_service)

    result = agent.investigate(
        case_id="HHG-TESTING",
        trigger_transaction={
            "transaction_id": "T0",
            "card_id": "C1-K1",
            "customer_id": "C1",
            "amount": 150.0,
            "trigger_text": "Card testing sequence observed",
            "channel": "online",
        },
        customer={"customer_id": "C1"},
    )

    assert result.case.verdict is Verdict.FRAUD
    assert result.case.pattern is Pattern.CARD_TESTING
    assert result.case.fraud_probability >= 0.85
    assert result.case.status is CaseStatus.CLOSED_FRAUD

    # Check policy actions include DECLINE_TRANSACTION, STEP_UP_AUTH, and BLOCK_CARD (since cleared > 100)
    final_actions = {a.action for a in result.next_best_actions.final}
    assert Action.DECLINE_TRANSACTION in final_actions
    assert Action.STEP_UP_AUTH in final_actions
    assert Action.BLOCK_CARD in final_actions
    assert result.case.written_to_graph is False


def test_agent_weak_signal_customer_denies_and_high_exposure_sar():
    """Agent evaluates weak signal under R1, simulates customer denial under R2, and generates SAR for >$1,000 exposure."""
    graph_service = MockGraphEvidenceService()
    agent = InvestigationAgent(graph_service=graph_service)

    result = agent.investigate(
        case_id="HHG-WEAK-SIGNAL",
        trigger_transaction={
            "transaction_id": "T-HIGH",
            "card_id": "C2-K1",
            "customer_id": "C2",
            "amount": 2500.0,
            "risk_score": 0.75,
            "trigger_text": "Risk score alert",
            "channel": "online",
            "ts": "2016-11-15 14:00:00",
        },
        customer={"customer_id": "C2"},
        customer_response="denies",
    )

    # Initial action was VERIFY_WITH_CUSTOMER (under R1)
    init_actions = {a.action for a in result.next_best_actions.initial}
    assert Action.VERIFY_WITH_CUSTOMER in init_actions

    # Customer denied -> final actions include BLOCK_CARD, CREATE_CASE, and FILE_REPORT (since exposure > 1000)
    final_actions = {a.action for a in result.next_best_actions.final}
    assert Action.BLOCK_CARD in final_actions
    assert Action.CREATE_CASE in final_actions
    assert Action.FILE_REPORT in final_actions

    # SAR must be filed with structured narrative and 2 activity dates
    assert result.sar.file is True
    assert len(result.sar.activity_dates) == 2
    assert result.sar.total_amount_usd == 2500.0
    assert "2016-11-15" in result.sar.activity_dates[0]
    assert len(result.sar.narrative) > 50

    # Case record assertions
    assert result.case.verdict is Verdict.FRAUD
    assert result.case.exposure_usd == 2500.0
    assert result.case.written_to_graph is False


def test_agent_legitimate_customer_confirms():
    """Agent clears alert when customer confirms, verifying legitimate invariant (exposure=0, affected_txns=[])."""
    graph_service = MockGraphEvidenceService()
    agent = InvestigationAgent(graph_service=graph_service)

    result = agent.investigate(
        case_id="HHG-LEGIT-1",
        trigger_transaction={
            "transaction_id": "T-NORMAL",
            "card_id": "C3-K1",
            "customer_id": "C3",
            "amount": 89.99,
            "risk_score": 0.20,
            "trigger_text": "Routine check",
            "channel": "in_person",
        },
        customer={"customer_id": "C3"},
        customer_response="confirms",
    )

    assert result.case.verdict is Verdict.LEGITIMATE
    assert result.case.status is CaseStatus.CLOSED_LEGITIMATE
    assert result.case.exposure_usd == 0.0
    assert result.case.affected_txn_ids == []
    assert result.sar.file is False

    final_actions = {a.action for a in result.next_best_actions.final}
    assert Action.CLOSE_NO_FRAUD in final_actions
    assert result.case.written_to_graph is False


def test_agent_undocumented_pattern():
    """Agent handles undocumented coordinated abuse, emits required pattern description, and adheres to R9."""
    graph_service = MockGraphEvidenceService()
    agent = InvestigationAgent(graph_service=graph_service)

    init_state = InvestigationState(
        case_id="HHG-UNDOC-1",
        trigger_transaction={
            "transaction_id": "T-UNDOC",
            "card_id": "C4-K1",
            "customer_id": "C4",
            "amount": 1200.0,
            "trigger_type": "undocumented",
            "trigger_text": "undocumented coordinated cross-customer transaction cluster",
            "channel": "online",
            "device_profile_id": "DEV-SHARED-1",
            "ts": "2016-12-01 10:00:00",
        },
        customer={"customer_id": "C4"},
        connected_card_ids=["C4-K1", "C5-K1"],
        connected_device_profiles=["DEV-SHARED-1"],
    )

    final_state = agent.run(init_state)
    result = final_state.to_investigation_result()

    assert result.case.pattern is Pattern.UNDOCUMENTED
    assert result.case.pattern_description != ""
    assert result.case.verdict is Verdict.FRAUD

    # R9 mandates CREATE_CASE, FILE_REPORT, ESCALATE_TO_ANALYST
    final_actions = {a.action for a in result.next_best_actions.final}
    assert Action.CREATE_CASE in final_actions
    assert Action.FILE_REPORT in final_actions
    assert Action.ESCALATE_TO_ANALYST in final_actions

    assert result.sar.file is True
    assert result.case.written_to_graph is False
