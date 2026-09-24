#!/usr/bin/env python3
"""Batch Runner for Hacker House Goa 20-Case Benchmark.

Investigates all 20 cases from case_pack.csv using the live TigerGraph MCP client,
GraphRAG policy retrieval, closed-case historical memory, and InvestigationAgent.
Generates outputs/benchmark_answers.json and validates all outputs.
"""
from __future__ import annotations

import csv
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from app.investigation import (
    InMemoryClosedCaseRepository,
    InvestigationAgent,
    InvestigationCaseWriterStub,
    InvestigationState,
    PolicyRetriever,
    TigerGraphMCPEvidenceService,
)
from app.investigation.mcp_client import LiveTigerGraphMCPClient
from scripts.validate_benchmark import validate_benchmark


def run_benchmark(
    case_pack_path: str | Path = "data/raw/case_pack.csv",
    closed_cases_path: str | Path = "data/raw/closed_cases_history.csv",
    output_path: str | Path = "outputs/benchmark_answers.json",
) -> list[dict]:
    case_pack_file = Path(case_pack_path)
    if not case_pack_file.is_file():
        raise FileNotFoundError(f"Case pack file not found: {case_pack_file}")

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("STARTING 20-CASE BENCHMARK INVESTIGATION ENGINE")
    print("=" * 70)

    # 1. Initialize live TigerGraph MCP client and service
    print("[1/4] Connecting to TigerGraph Savanna via LiveTigerGraphMCPClient...")
    mcp_client = LiveTigerGraphMCPClient()
    graph_service = TigerGraphMCPEvidenceService(mcp_client=mcp_client)

    # 2. Load historical case memory from authoritative closed cases
    print("[2/4] Loading closed cases into historical memory repository...")
    case_repo = InMemoryClosedCaseRepository.from_csv(closed_cases_path)
    print(f"      Loaded {len(case_repo._cases)} closed cases as case memory.")

    # 3. Initialize GraphRAG policy retriever and case writer stub
    print("[3/4] Initializing GraphRAG policy retriever and agent...")
    policy_retriever = PolicyRetriever()
    case_writer = InvestigationCaseWriterStub()
    agent = InvestigationAgent(
        graph_service=graph_service,
        policy_retriever=policy_retriever,
        case_repository=case_repo,
        case_writer=case_writer,
    )

    # 4. Read case pack rows
    with case_pack_file.open("r", encoding="utf-8") as f:
        cases_pack = list(csv.DictReader(f))

    print(f"[4/4] Processing {len(cases_pack)} benchmark cases...")
    answers = []

    for i, row in enumerate(cases_pack, 1):
        case_id = row["case_id"]
        txn_id = row["flagged_txn_id"]
        card_id = row["card_id"]
        cust_id = row["customer_id"]
        trigger_type = row["trigger_type"]
        trigger_text = row["trigger_text"]
        raw_score = row.get("risk_score")
        risk_score = float(raw_score) if raw_score and raw_score.strip() else 0.0

        print(f"\n[{i:02d}/20] Investigating Case: {case_id} (Txn: {txn_id}, Trigger: {trigger_type})")

        # Determine initial customer response based on trigger
        if trigger_type == "customer_report":
            cust_response = "denies"
        elif trigger_type == "analyst_request":
            cust_response = None
        else:
            cust_response = None

        trigger_tx = {
            "transaction_id": txn_id,
            "TransactionID": txn_id,
            "card_id": card_id,
            "customer_id": cust_id,
            "risk_score": risk_score,
            "trigger_type": trigger_type,
            "trigger_text": trigger_text,
            "ts": row.get("opened_at", ""),
        }

        # Run stateful investigation agent
        init_state = InvestigationState(
            case_id=case_id,
            trigger_transaction=trigger_tx,
            customer={"customer_id": cust_id},
            customer_response=cust_response,
        )

        final_state = agent.run(init_state)
        res = final_state.to_investigation_result()
        case_rec = res.case
        nba = res.next_best_actions
        sar_rec = res.sar

        # Construct JSON answer satisfying all required dimensions and Phase 3 contracts
        answer = {
            "case_id": case_id,
            "flagged_transaction_id": txn_id,
            "status": case_rec.status.value,
            "investigation_status": case_rec.status.value,
            "verdict": case_rec.verdict.value,
            "fraud_probability": round(case_rec.fraud_probability, 4),
            "uncertainty": round(final_state.uncertainty, 4),
            "pattern": case_rec.pattern.value,
            "pattern_description": case_rec.pattern_description,
            "evidence": [ev.model_dump() for ev in case_rec.evidence],
            "evidence_requests": [req.model_dump(mode="json") for req in res.evidence_requests],
            "initial_recommendations": [rec.model_dump() for rec in nba.initial],
            "final_recommendations": [rec.model_dump() for rec in nba.final],
            "initial_recommendation": [rec.model_dump() for rec in nba.initial],
            "final_recommendation": [rec.model_dump() for rec in nba.final],
            "next_best_action": nba.model_dump(),
            "next_best_actions": nba.model_dump(),
            "sar_decision": sar_rec.model_dump(),
            "sar": sar_rec.model_dump(),
            "explanation": final_state.explanation or case_rec.summary,
            "case": case_rec.model_dump(),
            "stop_reason": res.stop_reason,
            "tool_calls": res.tool_calls,
            "tokens": res.tokens,
            "latency_s": res.latency_s,
        }
        answers.append(answer)

        # Write individual case JSON matching official dataset README schema
        cases_dir = ROOT / "cases"
        cases_dir.mkdir(parents=True, exist_ok=True)
        case_file = cases_dir / f"{case_id}.json"
        case_official_payload = {
            "case_id": case_id,
            "case": case_rec.model_dump(),
            "evidence_requests": [req.model_dump(mode="json") for req in res.evidence_requests],
            "next_best_actions": nba.model_dump(),
            "sar": sar_rec.model_dump(),
            "stop_reason": res.stop_reason,
            "tool_calls": res.tool_calls,
            "tokens": res.tokens,
            "latency_s": res.latency_s,
        }
        with case_file.open("w", encoding="utf-8") as f:
            json.dump(case_official_payload, f, indent=2)

        print(f"      -> Verdict: {case_rec.verdict.value.upper()} | Pattern: {case_rec.pattern.value}")
        print(f"      -> Probability: {case_rec.fraud_probability:.2f} | Exposure: ${case_rec.exposure_usd:,.2f}")
        print(f"      -> SAR Filed: {sar_rec.file} | Final Actions: {[a.action.value for a in nba.final]}")

    # Write output JSON
    payload = {"cases": answers, "total_cases": len(answers), "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")}
    with out_file.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print("\n" + "=" * 70)
    print(f"SAVED {len(answers)} BENCHMARK ANSWERS TO: {out_file}")
    print(f"SAVED 20 INDIVIDUAL CASE FILES TO: {ROOT / 'cases'}")
    print("=" * 70)

    # Validate output immediately
    print("\nRunning automated validation check...")
    val_result = validate_benchmark(out_file)
    if not val_result["valid"]:
        raise RuntimeError("Benchmark validation failed!")

    return answers


if __name__ == "__main__":
    run_benchmark()
