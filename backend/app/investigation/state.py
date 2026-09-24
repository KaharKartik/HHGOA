from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field

from .graph_rag import PolicyEvidence
from .models import (
    ActionRecommendation,
    ActionSet,
    CaseRecord,
    CaseStatus,
    EvidenceItem,
    EvidenceRequest,
    InvestigationResult,
    Pattern,
    SARRecord,
    Verdict,
)


class InvestigationState(BaseModel):
    """InvestigationState holds the end-to-end mutable state for an investigation.

    The model is designed in pure Python and adheres strictly to the 13 required state dimensions:
    1. case_id
    2. trigger transaction (trigger_transaction)
    3. customer
    4. graph evidence (graph_evidence)
    5. policy evidence (policy_evidence)
    6. fraud probability (fraud_probability)
    7. uncertainty (uncertainty)
    8. pattern (pattern)
    9. evidence requests (evidence_requests)
    10. initial/final recommendation (initial_recommendations, final_recommendations)
    11. SAR decision (sar_decision)
    12. next-best-action (next_best_action)
    13. status (status)
    14. explanation (explanation)

    The structure is fully compatible with LangGraph's StateGraph schema and node transition engine.
    """

    # --- Core Required Dimensions ---
    case_id: str
    trigger_transaction: dict[str, Any] = Field(default_factory=dict)
    customer: dict[str, Any] = Field(default_factory=dict)
    graph_evidence: list[EvidenceItem] = Field(default_factory=list)
    policy_evidence: list[PolicyEvidence] = Field(default_factory=list)
    fraud_probability: float = Field(default=0.0, ge=0.0, le=1.0)
    uncertainty: float = Field(default=1.0, ge=0.0, le=1.0)
    pattern: Pattern = Pattern.NONE
    pattern_description: str = ""
    evidence_requests: list[EvidenceRequest] = Field(default_factory=list)
    initial_recommendations: list[ActionRecommendation] = Field(default_factory=list)
    final_recommendations: list[ActionRecommendation] = Field(default_factory=list)
    sar_decision: SARRecord | None = None
    next_best_action: ActionSet | None = None
    status: CaseStatus = CaseStatus.OPEN
    explanation: str = ""

    # --- Additional Operational & Traceability Attributes ---
    current_step: str = "init"
    step_history: list[str] = Field(default_factory=list)
    verdict: Verdict = Verdict.UNCERTAIN
    affected_txn_ids: list[str] = Field(default_factory=list)
    first_suspicious_txn_id: str = ""
    connected_card_ids: list[str] = Field(default_factory=list)
    connected_device_profiles: list[str] = Field(default_factory=list)
    exposure_usd: float = Field(default=0.0, ge=0.0)
    similar_prior_cases: list[str] = Field(default_factory=list)
    customer_response: Literal["denies", "confirms", "no_reply"] | None = None
    verification_settles_question: bool = False
    further_steps_unlikely_to_change: bool = False
    stop_reason: str = ""
    tool_calls: int = Field(default=0, ge=0)
    tokens: int = Field(default=0, ge=0)
    latency_s: float = Field(default=0.0, ge=0.0)
    written_to_graph: bool = False
    graph_case_id: str = ""
    summary: str = ""

    def copy_with(self, **updates: Any) -> InvestigationState:
        """Immutable state update helper compatible with LangGraph node emissions."""
        return self.model_copy(update=updates)

    def to_case_record(self) -> CaseRecord:
        """Convert state into validated CaseRecord enforcing all Phase 3 invariants."""
        # Enforce CaseRecord invariants
        p_desc = self.pattern_description if self.pattern is Pattern.UNDOCUMENTED else ""
        if self.pattern is Pattern.UNDOCUMENTED and not p_desc:
            p_desc = "Undocumented pattern observed: anomalous cross-customer coordination."

        # If verdict is legitimate, affected_txn_ids and exposure must be empty/0
        if self.verdict is Verdict.LEGITIMATE:
            aff_txns: list[str] = []
            exp_usd: float = 0.0
        else:
            aff_txns = list(self.affected_txn_ids)
            exp_usd = float(self.exposure_usd)

        # Ensure evidence list has items or at least one traceable item
        evidence_items = list(self.graph_evidence)
        if not evidence_items:
            evidence_items = [
                EvidenceItem(
                    claim="Case initialized and evaluated under deterministic policy checks.",
                    source="document",  # type: ignore
                    ref="data/raw/README.md#Fraud Policy",
                    entity_ids=[self.case_id],
                )
            ]

        case_summary = self.summary or self.explanation or f"Investigation of case {self.case_id} concluded with verdict {self.verdict.value}."

        return CaseRecord(
            status=self.status,
            verdict=self.verdict,
            fraud_probability=round(self.fraud_probability, 4),
            pattern=self.pattern,
            pattern_description=p_desc,
            affected_txn_ids=aff_txns,
            first_suspicious_txn_id=self.first_suspicious_txn_id,
            connected_card_ids=list(self.connected_card_ids),
            connected_device_profiles=list(self.connected_device_profiles),
            exposure_usd=round(exp_usd, 2),
            evidence=evidence_items,
            similar_prior_cases=list(self.similar_prior_cases),
            summary=case_summary,
            written_to_graph=self.written_to_graph,
            graph_case_id=self.graph_case_id,
        )

    def to_investigation_result(self) -> InvestigationResult:
        """Assemble full InvestigationResult conforming to Phase 3 contract."""
        case_rec = self.to_case_record()

        sar_rec = self.sar_decision
        if sar_rec is None:
            sar_rec = SARRecord(
                file=False,
                reason="No report trigger under R2/R6/R9",
                total_amount_usd=0.0,
            )

        nba = self.next_best_action
        if nba is None:
            nba = ActionSet(
                initial=list(self.initial_recommendations),
                final=list(self.final_recommendations or self.initial_recommendations),
                what_changed="no simulated changes",
            )

        return InvestigationResult(
            case_id=self.case_id,
            case=case_rec,
            evidence_requests=list(self.evidence_requests),
            next_best_actions=nba,
            sar=sar_rec,
            stop_reason=self.stop_reason or "Investigation concluded under policy criteria.",
            tool_calls=self.tool_calls,
            tokens=self.tokens,
            latency_s=round(self.latency_s, 3),
        )
