#!/usr/bin/env python3
"""FastAPI backend for the fraud investigation platform.

Endpoints:
  GET  /cases                          - list all 20 benchmark cases with basic status
  GET  /cases/{case_id}                - investigate a specific case and return full evidence/reasoning
  GET  /transactions/search            - search transactions by ID, customer, card, or device
  GET  /transactions/{transaction_id}  - retrieve full graph context for a single transaction
  GET  /health                         - health check
"""
from __future__ import annotations

import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from urllib.request import Request, urlopen

from app.investigation import (
    InMemoryClosedCaseRepository,
    InvestigationAgent,
    InvestigationCaseWriterStub,
    InvestigationState,
    PolicyRetriever,
    TigerGraphMCPEvidenceService,
)
from app.investigation.mcp_client import LiveTigerGraphMCPClient
from app.integrations.tigergraph import TigerGraphAdapter

app = FastAPI(
    title="HH Goa Fraud Investigation API",
    description="MVP endpoint for case investigation using TigerGraph + PolicyEngine + GraphRAG",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Shared state ─────────────────────────────────────────────────────────────
_CASE_PACK_FILE = ROOT / "data" / "raw" / "case_pack.csv"
_CLOSED_CASES_FILE = ROOT / "data" / "raw" / "closed_cases_history.csv"
_BENCHMARK_FILE = ROOT / "outputs" / "benchmark_answers.json"

_case_pack: list[dict[str, str]] = []
_case_pack_index: dict[str, dict[str, str]] = {}
_closed_cases: list[dict[str, str]] = []
_closed_cases_by_customer: dict[str, list[dict[str, str]]] = {}
_closed_cases_by_card: dict[str, list[dict[str, str]]] = {}
_closed_cases_by_txn: dict[str, list[dict[str, str]]] = {}
_agent: InvestigationAgent | None = None
_mcp_client: LiveTigerGraphMCPClient | None = None
_graph_service: TigerGraphMCPEvidenceService | None = None
_tg_adapter: TigerGraphAdapter | None = None
_benchmark_cache: dict[str, Any] = {}


def _load_case_pack() -> None:
    global _case_pack, _case_pack_index
    if _case_pack:
        return
    with _CASE_PACK_FILE.open("r", encoding="utf-8") as f:
        _case_pack = list(csv.DictReader(f))
    _case_pack_index = {row["case_id"]: row for row in _case_pack}


def _load_closed_cases() -> None:
    global _closed_cases, _closed_cases_by_customer, _closed_cases_by_card, _closed_cases_by_txn
    if _closed_cases:
        return
    if not _CLOSED_CASES_FILE.is_file():
        return
    with _CLOSED_CASES_FILE.open("r", encoding="utf-8") as f:
        _closed_cases = list(csv.DictReader(f))
    for c in _closed_cases:
        cid = c.get("customer_id", "").strip()
        if cid:
            _closed_cases_by_customer.setdefault(cid, []).append(c)
        card_id = c.get("card_id", "").strip()
        if card_id:
            _closed_cases_by_card.setdefault(card_id, []).append(c)
        for tid in c.get("txn_ids", "").split(","):
            tid = tid.strip()
            if tid:
                _closed_cases_by_txn.setdefault(tid, []).append(c)


def _load_benchmark_cache() -> None:
    global _benchmark_cache
    if _benchmark_cache or not _BENCHMARK_FILE.is_file():
        return
    with _BENCHMARK_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)
    cases = data.get("cases", data) if isinstance(data, dict) else data
    for c in cases:
        _benchmark_cache[c["case_id"]] = c


def _get_mcp_client() -> LiveTigerGraphMCPClient:
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = LiveTigerGraphMCPClient()
    return _mcp_client


def _get_graph_service() -> TigerGraphMCPEvidenceService:
    global _graph_service
    if _graph_service is None:
        _graph_service = TigerGraphMCPEvidenceService(mcp_client=_get_mcp_client())
    return _graph_service


def _get_tg_adapter() -> TigerGraphAdapter:
    """Return a TigerGraphAdapter initialised from the absolute project .env path.
    Using ROOT / ".env" avoids the CWD-relative lookup that fails when uvicorn
    starts from the backend/ sub-directory.
    """
    global _tg_adapter
    if _tg_adapter is None:
        try:
            _tg_adapter = TigerGraphAdapter.from_environment(ROOT / ".env")
        except Exception:
            # Fallback: attempt without explicit path (env vars may already be set)
            _tg_adapter = TigerGraphAdapter.from_environment()
    return _tg_adapter


def _tg_get(adapter: TigerGraphAdapter, path: str, params: dict | None = None) -> dict:
    """Direct REST++ GET helper that mirrors LiveTigerGraphMCPClient._http_get."""
    from urllib.parse import urlencode as _urlencode
    url = adapter._restpp_url(path)
    if params:
        url = f"{url}?{_urlencode(params)}"
    req = Request(url, headers=adapter._headers())
    try:
        with urlopen(req, timeout=adapter.timeout_s) as resp:
            content = resp.read().decode("utf-8")
            try:
                return json.loads(content)
            except Exception:
                return {"error": True, "message": content[:200], "results": []}
    except Exception as err:
        return {"error": True, "message": str(err), "results": []}


def _get_agent() -> InvestigationAgent:
    global _agent
    if _agent is None:
        graph_service = _get_graph_service()
        case_repo = InMemoryClosedCaseRepository.from_csv(_CLOSED_CASES_FILE)
        _agent = InvestigationAgent(
            graph_service=graph_service,
            policy_retriever=PolicyRetriever(),
            case_repository=case_repo,
            case_writer=InvestigationCaseWriterStub(),
        )
    return _agent


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "fraud-investigation-api"}


@app.get("/cases")
def list_cases():
    """Return all 20 benchmark cases with basic metadata."""
    _load_case_pack()
    _load_benchmark_cache()
    result = []
    for row in _case_pack:
        case_id = row["case_id"]
        cached = _benchmark_cache.get(case_id, {})
        result.append({
            "case_id": case_id,
            "opened_at": row["opened_at"],
            "trigger_type": row["trigger_type"],
            "trigger_text": row["trigger_text"],
            "flagged_txn_id": row["flagged_txn_id"],
            "card_id": row["card_id"],
            "customer_id": row["customer_id"],
            "risk_score": row.get("risk_score") or None,
            # Include cached result if benchmark has already been run
            "verdict": cached.get("verdict"),
            "fraud_probability": cached.get("fraud_probability"),
            "pattern": cached.get("pattern"),
            "status": cached.get("status") or cached.get("investigation_status"),
        })
    return {"cases": result, "total": len(result)}


@app.get("/cases/{case_id}")
def investigate_case(case_id: str, force: bool = False):
    """Investigate a specific case. Uses cached benchmark result if available; re-runs if force=True."""
    _load_case_pack()
    _load_benchmark_cache()

    if case_id not in _case_pack_index:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found in case_pack.csv")

    # Return cached benchmark result unless forced re-run
    if not force and case_id in _benchmark_cache:
        cached = dict(_benchmark_cache[case_id])
        # Inject case-pack fields that GraphNodesGrid needs at the top level
        pack_row = _case_pack_index.get(case_id, {})
        cached.setdefault("card_id", pack_row.get("card_id"))
        cached.setdefault("customer_id", pack_row.get("customer_id"))
        cached.setdefault("transaction_id", pack_row.get("flagged_txn_id"))
        return cached

    # Live investigation
    row = _case_pack_index[case_id]
    txn_id = row["flagged_txn_id"]
    card_id = row["card_id"]
    cust_id = row["customer_id"]
    trigger_type = row["trigger_type"]
    trigger_text = row["trigger_text"]
    raw_score = row.get("risk_score", "")
    risk_score = float(raw_score) if raw_score and raw_score.strip() else 0.0

    cust_response = "denies" if trigger_type == "customer_report" else None

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

    agent = _get_agent()
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

    answer = {
        "case_id": case_id,
        "flagged_transaction_id": txn_id,
        "status": case_rec.status.value,
        "verdict": case_rec.verdict.value,
        "fraud_probability": round(case_rec.fraud_probability, 4),
        "uncertainty": round(final_state.uncertainty, 4),
        "pattern": case_rec.pattern.value,
        "pattern_description": case_rec.pattern_description,
        "evidence": [ev.model_dump() for ev in case_rec.evidence],
        "initial_recommendations": [rec.model_dump() for rec in nba.initial],
        "final_recommendations": [rec.model_dump() for rec in nba.final],
        "next_best_action": nba.model_dump(),
        "sar_decision": sar_rec.model_dump(),
        "explanation": final_state.explanation or case_rec.summary,
        "case": case_rec.model_dump(),
        "stop_reason": res.stop_reason,
        "tool_calls": res.tool_calls,
        "latency_s": res.latency_s,
    }
    return JSONResponse(content=answer)


@app.get("/transactions/search")
def search_transactions(
    q: str = Query(..., min_length=1, description="Search term (txn ID, customer ID, card ID, or device ID)"),
    type: str = Query("all", description="Search filter: all, transaction, customer, card, device"),
    limit: int = Query(20, ge=1, le=100),
):
    """Search transactions across live TigerGraph and dataset by transaction_id, customer_id, card_id, or device_profile_id."""
    t0 = time.perf_counter()
    _load_case_pack()
    _load_closed_cases()
    q_str = q.strip()
    client = _get_mcp_client()

    results: list[dict[str, Any]] = []
    seen_txns: set[str] = set()

    def add_txn(txn_id: str, matched_by: str, extra: dict[str, Any] | None = None):
        if not txn_id or txn_id in seen_txns:
            return
        seen_txns.add(txn_id)
        item = {
            "transaction_id": txn_id,
            "matched_by": matched_by,
            "customer_id": None,
            "card_id": None,
            "amount": None,
            "channel": None,
            "ts": None,
            "billing_region": None,
            "purchaser_email": None,
            "device_profile_id": None,
            "risk_score": None,
            "associated_case_id": None,
        }
        if extra:
            item.update({k: v for k, v in extra.items() if v is not None})
        results.append(item)

    # 1. Search in Case Pack (20 benchmark cases)
    for row in _case_pack:
        case_id = row.get("case_id")
        txn_id = row.get("flagged_txn_id")
        cust_id = row.get("customer_id")
        card_id = row.get("card_id")
        score = float(row.get("risk_score") or 0.0) if row.get("risk_score") else None

        match = False
        matched_by = "case_pack"
        if type in ("all", "transaction") and q_str == txn_id:
            match = True
            matched_by = "transaction_id"
        elif type in ("all", "customer") and q_str.lower() == (cust_id or "").lower():
            match = True
            matched_by = "customer_id"
        elif type in ("all", "card") and q_str.lower() == (card_id or "").lower():
            match = True
            matched_by = "card_id"
        elif type == "all" and (q_str in (case_id or "") or q_str in (row.get("trigger_text") or "")):
            match = True
            matched_by = "text_match"

        if match and txn_id:
            add_txn(txn_id, matched_by, {
                "customer_id": cust_id,
                "card_id": card_id,
                "risk_score": score,
                "ts": row.get("opened_at"),
                "associated_case_id": case_id,
            })

    # 2. Search in Closed Cases History
    if type in ("all", "transaction") and q_str in _closed_cases_by_txn:
        for c in _closed_cases_by_txn[q_str]:
            add_txn(q_str, "transaction_id", {
                "customer_id": c.get("customer_id"),
                "card_id": c.get("card_id"),
                "amount": float(c.get("exposure_usd") or 0.0) if c.get("exposure_usd") else None,
                "ts": c.get("opened_at"),
                "associated_case_id": c.get("case_id"),
            })

    if type in ("all", "customer") and q_str.upper() in _closed_cases_by_customer:
        for c in _closed_cases_by_customer[q_str.upper()][:limit]:
            tid = c.get("first_fraud_txn_id") or (c.get("txn_ids", "").split(",")[0] if c.get("txn_ids") else "")
            if tid:
                add_txn(tid, "customer_id", {
                    "customer_id": c.get("customer_id"),
                    "card_id": c.get("card_id"),
                    "amount": float(c.get("exposure_usd") or 0.0) if c.get("exposure_usd") else None,
                    "ts": c.get("opened_at"),
                    "associated_case_id": c.get("case_id"),
                })

    if type in ("all", "card") and q_str.upper() in _closed_cases_by_card:
        for c in _closed_cases_by_card[q_str.upper()][:limit]:
            tid = c.get("first_fraud_txn_id") or (c.get("txn_ids", "").split(",")[0] if c.get("txn_ids") else "")
            if tid:
                add_txn(tid, "card_id", {
                    "customer_id": c.get("customer_id"),
                    "card_id": c.get("card_id"),
                    "amount": float(c.get("exposure_usd") or 0.0) if c.get("exposure_usd") else None,
                    "ts": c.get("opened_at"),
                    "associated_case_id": c.get("case_id"),
                })

    # 3. Direct Live TigerGraph Query
    if type in ("all", "transaction") and q_str not in seen_txns and (q_str.isdigit() or len(q_str) >= 6):
        try:
            tg_tx = client.call_tool("tigergraph__get_node", {"vertex_type": "Transaction", "vertex_id": q_str})
            results_tg = tg_tx.get("results", [])
            if results_tg:
                v = results_tg[0]
                attrs = v.get("attributes", {})
                add_txn(q_str, "transaction_id", {
                    "customer_id": attrs.get("customer_id"),
                    "amount": attrs.get("amount"),
                    "channel": attrs.get("channel"),
                    "ts": attrs.get("ts"),
                    "billing_region": attrs.get("billing_region"),
                    "purchaser_email": attrs.get("purchaser_email"),
                })
        except Exception:
            pass

    # Direct TigerGraph query for Customer
    if type in ("all", "customer") and len(results) < limit and q_str.upper().startswith("C") and "-K" not in q_str.upper():
        try:
            tg_c = client.call_tool("tigergraph__get_node", {"vertex_type": "Customer", "vertex_id": q_str.upper()})
            if tg_c.get("results"):
                # Customer exists in TigerGraph
                pass
        except Exception:
            pass

    # Populate missing attributes for top results from TigerGraph
    for item in results[:15]:
        tid = item["transaction_id"]
        if item["amount"] is None or item["channel"] is None or item["billing_region"] is None or item["device_profile_id"] is None:
            try:
                tg_tx = client.call_tool("tigergraph__get_node", {"vertex_type": "Transaction", "vertex_id": tid})
                tg_res = tg_tx.get("results", [])
                if tg_res:
                    attrs = tg_res[0].get("attributes", {})
                    item["customer_id"] = item["customer_id"] or attrs.get("customer_id")
                    item["amount"] = item["amount"] if item["amount"] is not None else attrs.get("amount")
                    item["channel"] = item["channel"] or attrs.get("channel")
                    item["ts"] = item["ts"] or attrs.get("ts")
                    item["billing_region"] = item["billing_region"] or attrs.get("billing_region")
                    item["purchaser_email"] = item["purchaser_email"] or attrs.get("purchaser_email")

                edges_res = client.call_tool("tigergraph__get_node_edges", {"vertex_type": "Transaction", "vertex_id": tid})
                for e in edges_res.get("results", []):
                    if e.get("e_type") == "FROM_DEVICE":
                        item["device_profile_id"] = e.get("to_id")
                    elif e.get("e_type") == "PURCHASER_EMAIL" and not item["purchaser_email"]:
                        item["purchaser_email"] = e.get("to_id")
                    elif e.get("e_type") == "BILLED_IN" and not item["billing_region"]:
                        item["billing_region"] = e.get("to_id")
            except Exception:
                pass

    latency_ms = round((time.perf_counter() - t0) * 1000, 2)
    return {
        "query": q_str,
        "type": type,
        "results": results[:limit],
        "total": len(results[:limit]),
        "latency_ms": latency_ms,
    }


@app.get("/transactions/{transaction_id}")
def get_transaction_details(transaction_id: str):
    """Retrieve full dynamic graph context for a specific transaction from TigerGraph.

    Uses TigerGraphAdapter with an absolute ROOT/.env path so the REST++ base
    URL is always resolved correctly, regardless of the uvicorn working directory.
    """
    t0 = time.perf_counter()
    _load_case_pack()
    _load_closed_cases()
    graph_svc = _get_graph_service()

    # Obtain the adapter (uses ROOT/.env — always the correct path)
    try:
        adapter = _get_tg_adapter()
    except Exception:
        adapter = None

    # ── 1. Fetch Transaction vertex from TigerGraph ──────────────────────────
    tx_attrs: dict[str, Any] = {}
    tg_source = False
    if adapter:
        raw = _tg_get(adapter, f"graph/{adapter.graph_name}/vertices/Transaction/{transaction_id}")
        results_list = raw.get("results", [])
        if results_list:
            tx_attrs = results_list[0].get("attributes", {})
            tg_source = True

    # ── 2. Fetch Transaction edges from TigerGraph ───────────────────────────
    edges: list[dict[str, Any]] = []
    if adapter:
        raw_e = _tg_get(adapter, f"graph/{adapter.graph_name}/edges/Transaction/{transaction_id}")
        edges = raw_e.get("results", [])

    # Case-pack fallback when TigerGraph returns nothing
    if not tx_attrs:
        for row in _case_pack:
            if row.get("flagged_txn_id") == transaction_id:
                tx_attrs = {
                    "transaction_id": transaction_id,
                    "customer_id": row.get("customer_id"),
                    "amount": None,
                    "channel": None,
                    "ts": row.get("opened_at"),
                    "billing_region": None,
                    "purchaser_email": None,
                }
                break

    if not tx_attrs and not edges:
        raise HTTPException(
            status_code=404,
            detail=f"Transaction {transaction_id} not found in TigerGraph or case pack."
        )

    # ── 3. Extract connected entity IDs from edges ───────────────────────────
    device_ids    = [e["to_id"] for e in edges if e.get("e_type") == "FROM_DEVICE"]
    email_domains = [e["to_id"] for e in edges if e.get("e_type") == "PURCHASER_EMAIL"]
    billing_regions = [e["to_id"] for e in edges if e.get("e_type") == "BILLED_IN"]
    next_tx_ids   = [e["to_id"] for e in edges if e.get("e_type") == "NEXT"]

    device_id = device_ids[0] if device_ids else None

    # ── 4. Retrieve DeviceProfile vertex details ─────────────────────────────
    device_data: dict[str, Any] = {}
    if device_id and adapter:
        raw_d = _tg_get(adapter, f"graph/{adapter.graph_name}/vertices/DeviceProfile/{device_id}")
        dev_list = raw_d.get("results", [])
        if dev_list:
            device_data = dev_list[0].get("attributes", {})
            device_data["device_profile_id"] = device_id
        else:
            device_data = {"device_profile_id": device_id}

    # ── 5. Card ID resolution ────────────────────────────────────────────────
    customer_id: str | None = tx_attrs.get("customer_id")
    card_id: str | None = None

    # Priority 1: exact txn match in case pack
    for row in _case_pack:
        if row.get("flagged_txn_id") == transaction_id:
            card_id = row.get("card_id")
            break
    # Priority 2: same customer in case pack
    if not card_id and customer_id:
        for row in _case_pack:
            if row.get("customer_id") == customer_id:
                card_id = row.get("card_id")
                break
    # Priority 3: closed cases
    if not card_id and customer_id:
        closed_for_cust = _closed_cases_by_customer.get(customer_id, [])
        if closed_for_cust:
            card_id = closed_for_cust[0].get("card_id")
    # Priority 4: TigerGraph Customer → Card edge
    if not card_id and customer_id and adapter:
        raw_cust_e = _tg_get(adapter, f"graph/{adapter.graph_name}/edges/Customer/{customer_id}")
        for e in raw_cust_e.get("results", []):
            if e.get("e_type") == "OWNS" and e.get("to_type") == "Card":
                card_id = e["to_id"]
                break
    # Priority 5: conventional K1 suffix guess validated against TigerGraph
    if not card_id and customer_id and adapter:
        potential_card = f"{customer_id}-K1"
        raw_card = _tg_get(adapter, f"graph/{adapter.graph_name}/vertices/Card/{potential_card}")
        if raw_card.get("results"):
            card_id = potential_card

    # ── 6. Prior Cases ───────────────────────────────────────────────────────
    prior_cases: list[dict[str, Any]] = []
    for row in _case_pack:
        if row.get("flagged_txn_id") == transaction_id or (
            customer_id and row.get("customer_id") == customer_id
        ):
            prior_cases.append({
                "case_id": row.get("case_id"),
                "status": "active_investigation",
                "trigger_type": row.get("trigger_type"),
                "trigger_text": row.get("trigger_text"),
                "opened_at": row.get("opened_at"),
                "risk_score": float(row.get("risk_score") or 0.0) if row.get("risk_score") else None,
            })
    if customer_id and customer_id in _closed_cases_by_customer:
        for c in _closed_cases_by_customer[customer_id][:5]:
            prior_cases.append({
                "case_id": c.get("case_id"),
                "status": "closed",
                "outcome": c.get("outcome"),
                "pattern": c.get("pattern"),
                "exposure_usd": float(c.get("exposure_usd") or 0.0) if c.get("exposure_usd") else None,
                "opened_at": c.get("opened_at"),
                "closed_at": c.get("closed_at"),
                "actions_taken": c.get("actions_taken"),
            })

    # ── 7. Customer Transaction History ─────────────────────────────────────
    customer_history: list[dict[str, Any]] = []
    if customer_id:
        try:
            customer_history = graph_svc.get_customer_history(
                customer_id, "2016-01-01 00:00:00", "2017-01-01 00:00:00", limit=20
            )
        except Exception:
            customer_history = []

    # ── 8. Next/Sequence Transactions ───────────────────────────────────────
    sequence: list[dict[str, Any]] = [
        {"transaction_id": n_id, "direction": "NEXT"} for n_id in next_tx_ids[:5]
    ]

    # Resolved email / billing from vertex attrs or edge endpoints
    resolved_email  = tx_attrs.get("purchaser_email") or (email_domains[0] if email_domains else None)
    resolved_region = tx_attrs.get("billing_region")  or (billing_regions[0] if billing_regions else None)
    # Strip empty strings so the frontend sees None
    if not resolved_email:  resolved_email  = None
    if not resolved_region: resolved_region = None

    latency_ms = round((time.perf_counter() - t0) * 1000, 2)

    return {
        "transaction_id": transaction_id,
        "details": {
            "transaction_id": transaction_id,
            "customer_id": customer_id,
            "card_id": card_id,
            "amount": tx_attrs.get("amount"),
            "channel": tx_attrs.get("channel"),
            "product_cd": tx_attrs.get("product_cd"),
            "ts": tx_attrs.get("ts"),
            "billing_region": resolved_region,
            "purchaser_email": resolved_email,
        },
        # Top-level shorthand fields consumed by GraphNodesGrid
        "card_id": card_id,
        "customer_id": customer_id,
        "device": device_data,
        "device_profile_id": device_id,
        "email_domain": resolved_email,
        "billing_region": resolved_region,
        "sequence": sequence,
        "connected_entities": {
            "customer_id": customer_id,
            "card_id": card_id,
            "device_profile_id": device_id,
            "email_domain": email_domains[0] if email_domains else None,
            "billing_region": resolved_region,
            "next_transactions": next_tx_ids,
        },
        "prior_cases": prior_cases,
        "customer_context": {
            "customer_id": customer_id,
            "card_id": card_id,
            "total_prior_cases": len(prior_cases),
            "history": customer_history,
        },
        "latency_ms": latency_ms,
        "source": "tigergraph_live" if tg_source else "dataset",
    }
