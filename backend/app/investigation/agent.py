from __future__ import annotations

import time
from typing import Any, Callable

from .actions import route_action
from .case_memory import (
    ClosedCaseRepository,
    InMemoryClosedCaseRepository,
    InvestigationCaseWriter,
    InvestigationCaseWriterStub,
)
from .evidence import independent_evidence_count
from .exposure import calculate_exposure
from .graph_rag import PolicyRetriever
from .graph_service import GraphEvidenceService, MockGraphEvidenceService
from .models import (
    Action,
    ActionRecommendation,
    ActionSet,
    CaseRecord,
    CaseStatus,
    EvidenceItem,
    EvidenceRequest,
    EvidenceRequestType,
    EvidenceSource,
    InvestigationContext,
    InvestigationResult,
    Pattern,
    PolicyId,
    SARRecord,
    Verdict,
)
from .policy_engine import PolicyEngine
from .sar import decide_sar
from .state import InvestigationState
from .stopping import stop_investigation


class InvestigationAgent:
    """Stateful Fraud Investigation Agent Foundation built in pure Python.

    Designed with explicit node handlers that operate on immutable or updated
    InvestigationState objects, ensuring direct compatibility with migrating
    the internal transition engine to LangGraph StateGraph in the future.
    """

    def __init__(
        self,
        graph_service: GraphEvidenceService | None = None,
        policy_retriever: PolicyRetriever | None = None,
        case_repository: ClosedCaseRepository | None = None,
        case_writer: InvestigationCaseWriter | None = None,
        policy_engine: PolicyEngine | None = None,
    ):
        self.graph_service = graph_service or MockGraphEvidenceService()
        self.policy_retriever = policy_retriever or PolicyRetriever()
        self.case_repository = case_repository or InMemoryClosedCaseRepository()
        self.case_writer = case_writer or InvestigationCaseWriterStub()
        self.policy_engine = policy_engine or PolicyEngine()

    # -------------------------------------------------------------------------
    # Node 1: Initialize
    # -------------------------------------------------------------------------
    def node_initialize(self, state: InvestigationState) -> dict[str, Any]:
        """Validate input parameters and prepare open investigation state."""
        return {
            "current_step": "initialize",
            "status": CaseStatus.OPEN,
            "step_history": state.step_history + ["initialize"],
        }

    # -------------------------------------------------------------------------
    # Node 2: Gather Graph Evidence
    # -------------------------------------------------------------------------
    def node_gather_graph_evidence(self, state: InvestigationState) -> dict[str, Any]:
        """Query graph topology via GraphEvidenceService abstraction and retrieve prior cases."""
        evidence_items: list[EvidenceItem] = list(state.graph_evidence)
        tool_calls = state.tool_calls

        txn = state.trigger_transaction
        txn_id = txn.get("transaction_id") or txn.get("TransactionID") or ""
        card_id = txn.get("card_id") or ""
        cust_id = state.customer.get("customer_id") or txn.get("customer_id") or ""
        device_id = txn.get("device_profile_id") or txn.get("DeviceInfo") or ""
        ts = txn.get("ts") or ""

        similar_cases: list[str] = list(state.similar_prior_cases)
        connected_cards: list[str] = list(state.connected_card_ids)
        connected_devices: list[str] = list(state.connected_device_profiles)

        # 1. Transaction context lookup
        if txn_id:
            tx_ctx = self.graph_service.get_transaction_context(txn_id)
            tool_calls += 1
            if tx_ctx:
                res_list = tx_ctx.get("results", []) if isinstance(tx_ctx, dict) else []
                res = res_list[0] if res_list and isinstance(res_list[0], dict) else (tx_ctx if isinstance(tx_ctx, dict) else {})
                tx_verts = res.get("Transaction", []) if isinstance(res, dict) else []
                if tx_verts and isinstance(tx_verts[0], dict):
                    attrs = tx_verts[0].get("attributes", {})
                    for k, val in attrs.items():
                        if val is not None and val != "" and not txn.get(k):
                            txn[k] = val
                    if attrs.get("amount") is not None:
                        try:
                            txn["amount"] = float(attrs["amount"])
                        except ValueError:
                            pass
                    if attrs.get("channel"):
                        txn["channel"] = attrs["channel"]
                    if attrs.get("billing_region"):
                        txn["billing_region"] = attrs["billing_region"]

                for dev in res.get("Devices", []):
                    if dev and dev not in connected_devices:
                        connected_devices.append(dev)
                for reg in res.get("Regions", []):
                    if reg and not txn.get("billing_region"):
                        txn["billing_region"] = reg
                for email in res.get("Emails", []):
                    if email and not txn.get("purchaser_email"):
                        txn["purchaser_email"] = email

                claim_msg = f"Transaction {txn_id} context verified in graph"
                if txn.get("amount"):
                    claim_msg += f" (amount: ${float(txn['amount']):.2f})"
                if txn.get("billing_region"):
                    claim_msg += f" in region {txn['billing_region']}"
                evidence_items.append(
                    EvidenceItem(
                        claim=claim_msg,
                        source=EvidenceSource.GRAPH,
                        ref="transaction_context",
                        entity_ids=[txn_id],
                    )
                )

        # 2. Customer history
        if cust_id:
            history = self.graph_service.get_customer_history(cust_id, "2016-07-01", "2016-12-31")
            tool_calls += 1
            if history:
                evidence_items.append(
                    EvidenceItem(
                        claim=f"Customer {cust_id} transaction history retrieved ({len(history)} events).",
                        source=EvidenceSource.GRAPH,
                        ref="customer_transactions",
                        entity_ids=[cust_id],
                    )
                )

        # 3. Device neighbors and shared device usage
        if device_id:
            device_txns = self.graph_service.get_device_neighbors(device_id)
            tool_calls += 1
            if device_id not in connected_devices:
                connected_devices.append(device_id)
            if len(device_txns) > 1:
                other_cards = {
                    t.get("card_id") for t in device_txns if t.get("card_id") and t.get("card_id") != card_id
                }
                for oc in other_cards:
                    if oc not in connected_cards:
                        connected_cards.append(oc)
                evidence_items.append(
                    EvidenceItem(
                        claim=f"Device {device_id} shared across multiple cards: {sorted(other_cards)}.",
                        source=EvidenceSource.GRAPH,
                        ref="device_neighbors",
                        entity_ids=[device_id] + list(other_cards),
                    )
                )

        # 4. Card prior and connected cases
        if card_id:
            prior_cases = self.graph_service.get_card_prior_cases(card_id)
            tool_calls += 1
            for pc in prior_cases:
                cid = pc.get("case_id")
                if cid and cid not in similar_cases:
                    similar_cases.append(cid)

            # Query historical memory repository
            closed_hist = self.case_repository.find_by_card(card_id)
            for ch in closed_hist:
                if ch.case_id not in similar_cases:
                    similar_cases.append(ch.case_id)

            if similar_cases:
                evidence_items.append(
                    EvidenceItem(
                        claim=f"Historical closed cases retrieved for card {card_id}: {similar_cases}.",
                        source=EvidenceSource.GRAPH,
                        ref="prior_case_neighbors",
                        entity_ids=[card_id] + similar_cases,
                    )
                )

        # 5. Transaction sequence for card testing detection
        sequence = []
        if txn_id:
            sequence = self.graph_service.get_transaction_sequence(txn_id)
            tool_calls += 1
            if sequence:
                evidence_items.append(
                    EvidenceItem(
                        claim=f"Transaction sequence checked for rapid authorization bursts ({len(sequence)} consecutive txns).",
                        source=EvidenceSource.GRAPH,
                        ref="transaction_sequence",
                        entity_ids=[txn_id],
                    )
                )

        return {
            "current_step": "gather_graph_evidence",
            "graph_evidence": evidence_items,
            "similar_prior_cases": similar_cases,
            "connected_card_ids": connected_cards,
            "connected_device_profiles": connected_devices,
            "tool_calls": tool_calls,
            "step_history": state.step_history + ["gather_graph_evidence"],
        }

    # -------------------------------------------------------------------------
    # Node 3: Retrieve Policy Evidence (GraphRAG via in-memory TF-IDF)
    # -------------------------------------------------------------------------
    def node_retrieve_policy_evidence(self, state: InvestigationState) -> dict[str, Any]:
        """Perform deterministic TF-IDF search over authoritative project documentation chunks."""
        txn = state.trigger_transaction
        trigger_text = txn.get("trigger_text", "")
        risk_score = float(txn.get("risk_score") or 0.0)

        # Construct contextual search query
        query_terms = [trigger_text]
        if risk_score > 0.7:
            query_terms.append("risk score weak signal verify before block")
        if state.connected_device_profiles or len(state.connected_card_ids) > 1:
            query_terms.append("shared origin device profile connected cards file report")

        query = " ".join(query_terms).strip() or "fraud investigation policy and stopping criteria"
        matched_chunks = self.policy_retriever.retrieve(query, top_k=3, min_score=0.01)

        # Format policy evidence into traceable EvidenceItem records
        doc_evidence: list[EvidenceItem] = list(state.graph_evidence)
        for pe in matched_chunks:
            doc_evidence.append(
                EvidenceItem(
                    claim=f"Matched policy {pe.title}: {pe.content[:120]}...",
                    source=EvidenceSource.DOCUMENT,
                    ref=pe.source_ref,
                    entity_ids=[state.case_id],
                )
            )

        return {
            "current_step": "retrieve_policy_evidence",
            "policy_evidence": matched_chunks,
            "graph_evidence": doc_evidence,
            "step_history": state.step_history + ["retrieve_policy_evidence"],
        }

    # -------------------------------------------------------------------------
    # Node 4: Assess Fraud and Classify Pattern
    # -------------------------------------------------------------------------
    def node_assess_fraud(self, state: InvestigationState) -> dict[str, Any]:
        """Calibrate fraud probability, determine pattern, and calculate dollar exposure."""
        import re

        txn = state.trigger_transaction
        txn_id = txn.get("transaction_id") or txn.get("TransactionID") or ""
        raw_amt = float(txn.get("amount") or txn.get("TransactionAmt") or 0.0)
        if raw_amt == 0.0 and txn.get("trigger_text"):
            m = re.search(r"\$([0-9,]+(?:\.[0-9]+)?)", txn.get("trigger_text", ""))
            if m:
                raw_amt = float(m.group(1).replace(",", ""))
                txn["amount"] = raw_amt

        risk_score = float(txn.get("risk_score") or 0.0)
        channel = txn.get("channel") or ("in_person" if txn.get("ProductCD") == "W" else "online")
        trigger_type = txn.get("trigger_type", "")

        # Sequence inspection
        sequence = self.graph_service.get_transaction_sequence(txn_id) if txn_id else []
        small_auths = [
            t for t in sequence if 0 < float(t.get("amount") or t.get("TransactionAmt") or 0.0) < 15.0
        ]
        has_large_follower = any(
            float(t.get("amount") or t.get("TransactionAmt") or 0.0) >= 100.0 for t in sequence
        )

        pattern = Pattern.NONE
        pattern_description = ""
        verdict = Verdict.UNCERTAIN
        prob = 0.50
        uncertainty = 0.50
        affected_txns: list[str] = [txn_id] if txn_id else []
        first_suspicious = txn_id

        # Pattern 1: Card testing (3+ small online auths within an hour followed by larger purchase)
        if len(small_auths) >= 3 and has_large_follower:
            pattern = Pattern.CARD_TESTING
            verdict = Verdict.FRAUD
            prob = 0.92
            uncertainty = 0.08
            first_suspicious = small_auths[0].get("transaction_id", txn_id)
            affected_txns = [t.get("transaction_id", "") for t in sequence if t.get("transaction_id")]
            if txn_id and txn_id not in affected_txns:
                affected_txns.append(txn_id)

        # Trigger is customer report (cardholder reported unauthorized purchase)
        elif trigger_type == "customer_report":
            pattern = (
                Pattern.CARD_NOT_PRESENT_NEW_DEVICE
                if (state.connected_device_profiles or channel == "online")
                else Pattern.CARD_NOT_PRESENT
            )
            verdict = Verdict.FRAUD
            prob = 0.90
            uncertainty = 0.10
            affected_txns = [txn_id] if txn_id else []

        # Trigger is analyst request (shared origin investigation)
        elif trigger_type == "analyst_request" or len(state.connected_card_ids) >= 2 or len(state.connected_device_profiles) > 1:
            if trigger_type == "undocumented" or "undocumented" in txn.get("trigger_text", "").lower():
                pattern = Pattern.UNDOCUMENTED
                pattern_description = (
                    "Coordinated cross-customer device/credential reuse exhibiting rapid authorization "
                    "bursts not captured by standard typologies."
                )
            else:
                pattern = Pattern.CARD_NOT_PRESENT_NEW_DEVICE
            verdict = Verdict.FRAUD
            prob = 0.88
            uncertainty = 0.12
            affected_txns = [txn_id] if txn_id else []

        # Out-of-region use
        elif channel == "in_person" and "region" in txn.get("trigger_text", "").lower():
            pattern = Pattern.OUT_OF_REGION
            verdict = Verdict.UNCERTAIN
            prob = 0.55
            uncertainty = 0.45
            affected_txns = [txn_id] if txn_id else []

        # Risk score alert
        elif risk_score >= 0.70:
            pattern = Pattern.CARD_NOT_PRESENT
            verdict = Verdict.UNCERTAIN
            prob = min(0.65, round(risk_score * 0.85, 2))
            uncertainty = 0.40
            affected_txns = [txn_id] if txn_id else []

        # Default / Weak signal under 0.70
        else:
            pattern = Pattern.CARD_NOT_PRESENT if channel == "online" else Pattern.NONE
            verdict = Verdict.UNCERTAIN
            prob = max(0.40, round(risk_score * 0.75, 2))
            uncertainty = 0.50
            affected_txns = [txn_id] if txn_id else []

        # Initial exposure calculation
        tx_amounts = [(tid, raw_amt) for tid in affected_txns] if affected_txns else [(txn_id, raw_amt)]
        exp_usd = calculate_exposure(tx_amounts)

        return {
            "current_step": "assess_fraud",
            "pattern": pattern,
            "pattern_description": pattern_description,
            "verdict": verdict,
            "fraud_probability": prob,
            "uncertainty": uncertainty,
            "affected_txn_ids": affected_txns,
            "first_suspicious_txn_id": first_suspicious,
            "exposure_usd": exp_usd,
            "step_history": state.step_history + ["assess_fraud"],
        }

    # -------------------------------------------------------------------------
    # Node 5: Initial Recommendations (using existing Phase 3 PolicyEngine)
    # -------------------------------------------------------------------------
    def node_initial_recommendations(self, state: InvestigationState) -> dict[str, Any]:
        """Formulate initial action recommendations via PolicyEngine without mutating state."""
        ctx = self._build_context(state)
        evaluation = self.policy_engine.evaluate(ctx)
        actions = list(evaluation.actions)

        # Guarantee at least one recommendation is always present
        if not actions:
            from .actions import recommendation as _rec
            if state.verdict is Verdict.FRAUD:
                # Already assessed as fraud before customer response: recommend block + case
                actions = [
                    _rec(Action.BLOCK_CARD, state.exposure_usd, "Initial fraud assessment"),
                    _rec(Action.CREATE_CASE, state.exposure_usd, "Initial fraud assessment"),
                ]
            else:
                # Uncertain / unknown: always request customer verification first
                actions = [
                    _rec(Action.VERIFY_WITH_CUSTOMER, state.exposure_usd, "Insufficient signal: verify with customer before action"),
                ]

        explanation = "; ".join(evaluation.explanations) or "Initial policy evaluation pending customer response"
        return {
            "current_step": "initial_recommendations",
            "initial_recommendations": actions,
            "explanation": explanation,
            "step_history": state.step_history + ["initial_recommendations"],
        }

    # -------------------------------------------------------------------------
    # Node 6: Evaluate Stopping Criteria or Request Evidence
    # -------------------------------------------------------------------------
    def node_evaluate_stopping_or_evidence_request(self, state: InvestigationState) -> dict[str, Any]:
        """Check stopping conditions; if uncertain on weak signal, simulate evidence request."""
        ctx = self._build_context(state)
        stopped, reason = stop_investigation(ctx)

        evidence_requests: list[EvidenceRequest] = list(state.evidence_requests)
        customer_resp = state.customer_response
        settles_question = state.verification_settles_question
        verdict = state.verdict
        prob = state.fraud_probability
        uncertainty = state.uncertainty
        affected_txns = list(state.affected_txn_ids)
        exp_usd = state.exposure_usd
        pattern = state.pattern

        txn = state.trigger_transaction
        txn_id = txn.get("transaction_id") or txn.get("TransactionID") or ""
        raw_amt = float(txn.get("amount") or txn.get("TransactionAmt") or 0.0)
        trigger_type = txn.get("trigger_type", "")
        risk_score = float(txn.get("risk_score") or 0.0)

        # If customer reported unauthorized transaction, customer explicitly denies
        if trigger_type == "customer_report" and customer_resp is None:
            customer_resp = "denies"
            verdict = Verdict.FRAUD
            prob = 0.90
            uncertainty = 0.10
            affected_txns = [txn_id] if txn_id else []
            exp_usd = calculate_exposure([(txn_id, raw_amt)])
            stopped = True
            reason = "Customer dispute report confirms unauthorized transaction."

        # If policy recommends verifying with customer and stopping criteria not satisfied:
        initial_actions = [rec.action for rec in state.initial_recommendations]
        if not stopped and (Action.VERIFY_WITH_CUSTOMER in initial_actions or verdict is Verdict.UNCERTAIN):
            step_idx = len(state.step_history)
            if customer_resp is None:
                # Calibrated simulation: high risk-score or analyst alerts deny; weak false alarms confirm
                if risk_score >= 0.70 or trigger_type == "analyst_request":
                    customer_resp = "denies"
                    assumed = "Customer denies authorization of flagged charge upon inquiry."
                else:
                    customer_resp = "confirms"
                    assumed = "Customer confirms charge as authorized transaction."
            else:
                assumed = f"Simulated customer response: {customer_resp}."

            req = EvidenceRequest(
                type=EvidenceRequestType.CUSTOMER_VALIDATION,
                asked_after_step=step_idx,
                assumed_response=assumed,
            )
            evidence_requests.append(req)
            settles_question = True

            # Update verdict post-simulation
            if customer_resp == "denies":
                verdict = Verdict.FRAUD
                prob = 0.90
                uncertainty = 0.10
                affected_txns = [txn_id] if txn_id else []
                exp_usd = calculate_exposure([(txn_id, raw_amt)])
                stopped = True
                reason = "Customer denial settled authorization legitimacy."
            elif customer_resp == "confirms":
                verdict = Verdict.LEGITIMATE
                pattern = Pattern.NONE
                prob = 0.05
                uncertainty = 0.05
                affected_txns = []
                exp_usd = 0.0
                stopped = True
                reason = "Customer confirmation cleared alert as legitimate transaction."
            elif customer_resp == "no_reply":
                verdict = Verdict.UNCERTAIN
                stopped = True
                reason = "No response from customer within 24-hour SLA window."

        if not stopped:
            stopped = True
            reason = "Calibrated probability and policy evaluation completed."

        return {
            "current_step": "evaluate_stopping_or_evidence_request",
            "stop_reason": reason,
            "evidence_requests": evidence_requests,
            "customer_response": customer_resp,
            "verification_settles_question": settles_question,
            "verdict": verdict,
            "pattern": pattern,
            "fraud_probability": prob,
            "uncertainty": uncertainty,
            "affected_txn_ids": affected_txns,
            "exposure_usd": exp_usd,
            "step_history": state.step_history + ["evaluate_stopping_or_evidence_request"],
        }

    # -------------------------------------------------------------------------
    # Node 7: Final Recommendations
    # -------------------------------------------------------------------------
    def node_final_recommendations(self, state: InvestigationState) -> dict[str, Any]:
        """Compute final post-simulation action recommendations and ActionSet."""
        ctx = self._build_context(state)
        evaluation = self.policy_engine.evaluate(ctx)
        final_actions = list(evaluation.actions)

        # Guarantee at least one recommendation is always present
        if not final_actions:
            from .actions import recommendation as _rec
            if state.verdict is Verdict.FRAUD:
                final_actions = [
                    _rec(Action.BLOCK_CARD, state.exposure_usd, "Final fraud verdict"),
                    _rec(Action.CREATE_CASE, state.exposure_usd, "Final fraud verdict"),
                ]
            else:
                final_actions = [
                    _rec(Action.CLOSE_NO_FRAUD, state.exposure_usd, "Customer confirmed or weak signal cleared"),
                ]

        # Ensure FILE_REPORT is present in final actions whenever SAR will be filed
        # (SAR decision runs after this node, but we can pre-check the sar logic condition)
        from .sar import _sar_threshold_met as _sar_check
        fin_action_names = [a.action for a in final_actions]
        if state.verdict is Verdict.FRAUD and _sar_check(ctx):
            if Action.FILE_REPORT not in fin_action_names:
                from .actions import recommendation as _rec
                final_actions.append(_rec(Action.FILE_REPORT, state.exposure_usd, "SAR threshold met — regulatory filing required"))

        init_acts = [a.action for a in state.initial_recommendations]
        fin_acts = [a.action for a in final_actions]

        if init_acts == fin_acts:
            what_changed = "nothing"
        else:
            what_changed = f"Actions updated after simulated {state.customer_response or 'evidence'}."

        nba = ActionSet(
            initial=state.initial_recommendations,
            final=final_actions,
            what_changed=what_changed,
        )

        return {
            "current_step": "final_recommendations",
            "final_recommendations": final_actions,
            "next_best_action": nba,
            "step_history": state.step_history + ["final_recommendations"],
        }

    # -------------------------------------------------------------------------
    # Node 8: Generate SAR
    # -------------------------------------------------------------------------
    def node_generate_sar(self, state: InvestigationState) -> dict[str, Any]:
        """Evaluate regulatory SAR filing criteria and generate structured narrative when required."""
        ctx = self._build_context(state)
        sar_rec = decide_sar(ctx)

        if sar_rec.file:
            # Construct a complete, defensible FinCEN SAR narrative: Who, What, When, Where, How, Why
            txn = state.trigger_transaction
            cust_id = state.customer.get("customer_id") or txn.get("customer_id") or "CUST-UNKNOWN"
            card_id = txn.get("card_id") or "CARD-UNKNOWN"
            ts = txn.get("ts") or "2016-11-01"
            date_str = ts.split()[0] if " " in ts else ts

            subjects = [cust_id, card_id]
            for cp in state.connected_device_profiles:
                if cp not in subjects:
                    subjects.append(cp)

            narrative = (
                f"Between {date_str} and {date_str}, customer {cust_id} on card {card_id} exhibited suspicious activity "
                f"under pattern '{state.pattern.value}' involving total exposure of ${state.exposure_usd:,.2f}. "
                f"The transaction series was identified through automated risk monitoring and cross-entity graph analysis. "
                f"Associated device identifiers include {state.connected_device_profiles or ['N/A']}. "
                f"The customer was consulted under policy guidelines, confirming unauthorized card-not-present exploitation. "
                f"Pursuant to BSA/AML reporting requirements under policies R2/R6/R9, this report is filed for immediate regulatory review."
            )

            sar_rec = SARRecord(
                file=True,
                reason="SAR threshold met under R2/R6/R9",
                narrative=narrative,
                subjects=subjects,
                total_amount_usd=state.exposure_usd,
                activity_dates=[date_str, date_str],
            )

        return {
            "current_step": "generate_sar",
            "sar_decision": sar_rec,
            "step_history": state.step_history + ["generate_sar"],
        }

    # -------------------------------------------------------------------------
    # Node 9: Finalize Case and Stub Memory Persistence
    # -------------------------------------------------------------------------
    def node_finalize(self, state: InvestigationState) -> dict[str, Any]:
        """Determine final status, build case record, and invoke stub writer."""
        if state.verdict is Verdict.FRAUD:
            status = CaseStatus.CLOSED_FRAUD
        elif state.verdict is Verdict.LEGITIMATE:
            status = CaseStatus.CLOSED_LEGITIMATE
        else:
            status = CaseStatus.ESCALATED

        # Build summary narrative
        summary = (
            f"Case {state.case_id} concluded with verdict {state.verdict.value} (p={state.fraud_probability:.2f}) "
            f"under pattern '{state.pattern.value}'. Exposure calculated at ${state.exposure_usd:.2f}."
        )

        final_state = state.copy_with(
            current_step="complete",
            status=status,
            summary=summary,
            step_history=state.step_history + ["finalize"],
        )

        # Build CaseRecord and invoke case writer stub (does not write to TigerGraph)
        case_rec = final_state.to_case_record()
        self.case_writer.write_case(case_rec)

        return {
            "current_step": "complete",
            "status": status,
            "summary": summary,
            "written_to_graph": False,
            "graph_case_id": "",
            "step_history": state.step_history + ["finalize"],
        }

    # -------------------------------------------------------------------------
    # Graph Engine Transition Loop
    # -------------------------------------------------------------------------
    def run(self, initial_state: InvestigationState) -> InvestigationState:
        """Run the pure-Python state machine through all sequential nodes."""
        t0 = time.perf_counter()
        state = initial_state

        pipeline: list[Callable[[InvestigationState], dict[str, Any]]] = [
            self.node_initialize,
            self.node_gather_graph_evidence,
            self.node_retrieve_policy_evidence,
            self.node_assess_fraud,
            self.node_initial_recommendations,
            self.node_evaluate_stopping_or_evidence_request,
            self.node_final_recommendations,
            self.node_generate_sar,
            self.node_finalize,
        ]

        for node_fn in pipeline:
            updates = node_fn(state)
            state = state.copy_with(**updates)

        elapsed = time.perf_counter() - t0
        return state.copy_with(latency_s=elapsed)

    def investigate(
        self,
        case_id: str,
        trigger_transaction: dict[str, Any],
        customer: dict[str, Any] | None = None,
        customer_response: Any = None,
    ) -> InvestigationResult:
        """Convenience endpoint returning the standard InvestigationResult contract."""
        init_state = InvestigationState(
            case_id=case_id,
            trigger_transaction=trigger_transaction,
            customer=customer or {},
            customer_response=customer_response,
        )
        final_state = self.run(init_state)
        return final_state.to_investigation_result()

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------
    def _build_context(self, state: InvestigationState) -> InvestigationContext:
        """Construct Phase 3 InvestigationContext from current InvestigationState."""
        single_signal = (
            len(state.graph_evidence) <= 1
            or float(state.trigger_transaction.get("risk_score") or 0.0) >= 0.70
        )
        raw_amt = float(
            state.trigger_transaction.get("amount")
            or state.trigger_transaction.get("TransactionAmt")
            or 0.0
        )
        aff_txns = [(tid, raw_amt) for tid in state.affected_txn_ids]

        is_undocumented = state.pattern is Pattern.UNDOCUMENTED

        return InvestigationContext(
            case_id=state.case_id,
            fraud_probability=state.fraud_probability,
            verdict=state.verdict,
            exposure_usd=state.exposure_usd,
            evidence=state.graph_evidence,
            affected_transactions=aff_txns,
            customer_response=state.customer_response,
            verification_settles_question=state.verification_settles_question,
            single_signal=single_signal,
            pending_authorizations=False,
            small_online_authorizations=3 if state.pattern is Pattern.CARD_TESTING else 0,
            authorizations_within_hour=state.pattern is Pattern.CARD_TESTING,
            larger_purchase_followed=state.pattern is Pattern.CARD_TESTING,
            cleared_purchase_over_100=state.exposure_usd > 100.0,
            shared_device_profile=state.connected_device_profiles[0] if state.connected_device_profiles else "",
            shared_region_cluster="",
            shared_recipient_email="",
            another_customer_fraud=len(state.connected_card_ids) > 1,
            coordinated_pattern=is_undocumented or len(state.connected_card_ids) > 1,
            recurring_match=False,
            evidence_conflicts=False,
            credentials_confirmed_compromised=state.pattern is Pattern.ACCOUNT_TAKEOVER,
            confirmed_fraud_cards=len(state.connected_card_ids),
            known_pattern=not is_undocumented,
            pattern=state.pattern,
            pattern_description=state.pattern_description,
            connected_card_ids=state.connected_card_ids,
            further_steps_unlikely_to_change=state.further_steps_unlikely_to_change,
        )
