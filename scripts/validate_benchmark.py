#!/usr/bin/env python3
"""Benchmark Answer Validator for Hacker House Goa Fraud Investigation.

Validates that outputs/benchmark_answers.json conforms to Phase 3 contracts,
contains all 20 benchmark cases from case_pack.csv with no fabricated IDs,
and adheres to all policy and schema invariants.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.investigation.models import (
    Action,
    ApprovalRoute,
    CaseStatus,
    EvidenceRequestType,
    Pattern,
    Verdict,
)

VALID_STATUSES = {s.value for s in CaseStatus}
VALID_VERDICTS = {v.value for v in Verdict}
VALID_PATTERNS = {p.value for p in Pattern}
VALID_ACTIONS = {a.value for a in Action}
VALID_ROUTES = {r.value for r in ApprovalRoute}
VALID_REQUEST_TYPES = {t.value for t in EvidenceRequestType}


def validate_benchmark(benchmark_file: str | Path = "outputs/benchmark_answers.json") -> dict:
    file_path = Path(benchmark_file)
    if not file_path.is_file():
        raise FileNotFoundError(f"Benchmark file not found: {file_path}")

    # Load authoritative case pack
    case_pack_file = ROOT / "data" / "raw" / "case_pack.csv"
    with case_pack_file.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        case_pack = {row["case_id"]: row for row in reader}

    expected_case_ids = set(case_pack.keys())
    if len(expected_case_ids) != 20:
        raise ValueError(f"Expected 20 cases in case_pack.csv, found {len(expected_case_ids)}")

    # Load benchmark answers
    with file_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    # Allow list or dict wrapped in "cases"
    if isinstance(data, dict) and "cases" in data:
        cases_list = data["cases"]
    elif isinstance(data, list):
        cases_list = data
    else:
        raise ValueError("benchmark_answers.json must be a list of 20 cases or a dict with a 'cases' list")

    if len(cases_list) != 20:
        raise ValueError(f"Benchmark must contain exactly 20 cases, found {len(cases_list)}")

    seen_case_ids = set()
    errors = []

    for idx, item in enumerate(cases_list):
        case_id = item.get("case_id")
        if not case_id:
            errors.append(f"Case at index {idx} missing 'case_id'")
            continue

        if case_id in seen_case_ids:
            errors.append(f"Duplicate case_id: {case_id}")
        seen_case_ids.add(case_id)

        if case_id not in expected_case_ids:
            errors.append(f"Unknown/fabricated case_id: {case_id}")
            continue

        pack_row = case_pack[case_id]
        expected_txn = str(pack_row["flagged_txn_id"]).strip()

        # Check transaction ID
        actual_txn = str(item.get("flagged_transaction_id") or "").strip()
        if actual_txn != expected_txn:
            errors.append(f"[{case_id}] Flagged transaction ID mismatch: expected {expected_txn}, got {actual_txn}")

        # Check status
        status = item.get("status") or item.get("investigation_status")
        if status not in VALID_STATUSES:
            errors.append(f"[{case_id}] Invalid status: {status}")

        # Check verdict
        verdict = item.get("verdict")
        if verdict not in VALID_VERDICTS:
            errors.append(f"[{case_id}] Invalid verdict: {verdict}")

        # Check probability and uncertainty
        prob = item.get("fraud_probability")
        if prob is None or not (0.0 <= float(prob) <= 1.0):
            errors.append(f"[{case_id}] Invalid fraud_probability: {prob}")

        uncertainty = item.get("uncertainty")
        if uncertainty is None or not (0.0 <= float(uncertainty) <= 1.0):
            errors.append(f"[{case_id}] Invalid uncertainty: {uncertainty}")

        # Check pattern
        pattern = item.get("pattern")
        if pattern not in VALID_PATTERNS:
            errors.append(f"[{case_id}] Invalid pattern: {pattern}")

        if pattern == Pattern.UNDOCUMENTED.value:
            p_desc = item.get("pattern_description")
            if not p_desc or len(p_desc.strip()) < 5:
                errors.append(f"[{case_id}] Undocumented pattern requires a non-empty pattern_description")

        # Check evidence
        evidence = item.get("evidence")
        if not evidence or not isinstance(evidence, list):
            errors.append(f"[{case_id}] Evidence must be a non-empty list")
        else:
            for e_idx, ev in enumerate(evidence):
                if not ev.get("claim") or not ev.get("source") or not ev.get("ref"):
                    errors.append(f"[{case_id}] Evidence item {e_idx} missing required fields (claim, source, ref)")
                if not ev.get("entity_ids"):
                    errors.append(f"[{case_id}] Evidence item {e_idx} missing entity_ids")

        # Check evidence_requests
        if "evidence_requests" not in item:
            errors.append(f"[{case_id}] Missing required field 'evidence_requests'")
        else:
            ev_requests = item["evidence_requests"]
            if not isinstance(ev_requests, list):
                errors.append(f"[{case_id}] 'evidence_requests' must be a list")
            else:
                for r_idx, req in enumerate(ev_requests):
                    if not isinstance(req, dict):
                        errors.append(f"[{case_id}] Evidence request {r_idx} must be a dictionary")
                        continue
                    req_type = req.get("type")
                    if req_type not in VALID_REQUEST_TYPES:
                        errors.append(f"[{case_id}] Invalid evidence request type: {req_type}")
                    if "asked_after_step" not in req or not isinstance(req["asked_after_step"], int) or req["asked_after_step"] < 0:
                        errors.append(f"[{case_id}] Evidence request {r_idx} missing valid integer asked_after_step")
                    if not req.get("assumed_response") or not isinstance(req["assumed_response"], str):
                        errors.append(f"[{case_id}] Evidence request {r_idx} missing non-empty assumed_response")

        # Check recommendations
        init_recs = item.get("initial_recommendations") or item.get("initial_recommendation")
        if not init_recs or not isinstance(init_recs, list):
            errors.append(f"[{case_id}] initial_recommendations must be a non-empty list")
        else:
            for r in init_recs:
                act = r.get("action")
                route = r.get("route")
                if act not in VALID_ACTIONS:
                    errors.append(f"[{case_id}] Invalid initial action: {act}")
                if route not in VALID_ROUTES:
                    errors.append(f"[{case_id}] Invalid initial approval route: {route}")

        final_recs = item.get("final_recommendations") or item.get("final_recommendation")
        if not final_recs or not isinstance(final_recs, list):
            errors.append(f"[{case_id}] final_recommendations must be a non-empty list")
        else:
            for r in final_recs:
                act = r.get("action")
                route = r.get("route")
                if act not in VALID_ACTIONS:
                    errors.append(f"[{case_id}] Invalid final action: {act}")
                if route not in VALID_ROUTES:
                    errors.append(f"[{case_id}] Invalid final approval route: {route}")

        # Check next_best_action
        nba = item.get("next_best_action") or item.get("next_best_actions")
        if not nba or not isinstance(nba, dict):
            errors.append(f"[{case_id}] next_best_action must be a dictionary")
        else:
            if "initial" not in nba or "final" not in nba or "what_changed" not in nba:
                errors.append(f"[{case_id}] next_best_action missing initial, final, or what_changed")

        # Check SAR decision
        sar = item.get("sar_decision") or item.get("sar")
        if not sar or not isinstance(sar, dict):
            errors.append(f"[{case_id}] sar_decision must be a dictionary")
        else:
            if "file" not in sar or "reason" not in sar:
                errors.append(f"[{case_id}] sar_decision missing 'file' or 'reason'")
            final_actions = {r.get("action") for r in (final_recs or [])}
            file_report_recommended = Action.FILE_REPORT.value in final_actions
            if sar.get("file") is True:
                if not file_report_recommended:
                    errors.append(f"[{case_id}] SAR file is True but FILE_REPORT is not in final actions")
                if not sar.get("narrative") or len(sar.get("narrative", "").strip()) < 20:
                    errors.append(f"[{case_id}] SAR file is True but narrative is missing or too short")
                dates = sar.get("activity_dates", [])
                if len(dates) != 2:
                    errors.append(f"[{case_id}] SAR file is True but activity_dates does not contain 2 dates")
                if float(sar.get("total_amount_usd", 0)) <= 0:
                    errors.append(f"[{case_id}] SAR file is True but total_amount_usd is <= 0")
            else:
                if file_report_recommended:
                    errors.append(f"[{case_id}] FILE_REPORT is in final actions but SAR file is False")
                if sar.get("narrative") or sar.get("total_amount_usd", 0) != 0:
                    errors.append(f"[{case_id}] Non-filed SAR must have empty narrative and 0 amount")

        # Check explanation
        explanation = item.get("explanation") or (item.get("case", {}) if isinstance(item.get("case"), dict) else {}).get("summary")
        if not explanation or len(str(explanation).strip()) < 10:
            errors.append(f"[{case_id}] Explanation is missing or too short")

        # Check legitimate invariant
        if verdict == Verdict.LEGITIMATE.value:
            case_obj = item.get("case") or {}
            exp = item.get("exposure_usd", case_obj.get("exposure_usd", 0))
            aff = item.get("affected_txn_ids", case_obj.get("affected_txn_ids", []))
            if float(exp) != 0.0 or len(aff) != 0:
                errors.append(f"[{case_id}] Legitimate case cannot have exposure > 0 or non-empty affected_txn_ids")

    if seen_case_ids != expected_case_ids:
        missing = expected_case_ids - seen_case_ids
        errors.append(f"Missing case IDs in benchmark: {sorted(missing)}")

    # ── Validate cases/ directory individual files ──────────────────────────────
    cases_dir = ROOT / "cases"
    if not cases_dir.is_dir():
        errors.append(f"Missing 'cases/' directory at repo root: {cases_dir}")
    else:
        case_files = sorted(list(cases_dir.glob("HHG-*.json")))
        if len(case_files) != 20:
            errors.append(f"Expected 20 files in cases/, found {len(case_files)}")
        
        for case_id in sorted(expected_case_ids):
            c_file = cases_dir / f"{case_id}.json"
            if not c_file.is_file():
                errors.append(f"Missing case file: cases/{case_id}.json")
                continue
            
            try:
                with c_file.open("r", encoding="utf-8") as f:
                    c_data = json.load(f)
            except Exception as e:
                errors.append(f"[cases/{case_id}.json] Failed to parse JSON: {e}")
                continue

            if c_data.get("case_id") != case_id:
                errors.append(f"[cases/{case_id}.json] case_id mismatch: expected {case_id}, got {c_data.get('case_id')}")

            # Check required top-level keys
            for req_key in ["case_id", "case", "evidence_requests", "next_best_actions", "sar", "stop_reason", "tool_calls", "tokens", "latency_s"]:
                if req_key not in c_data:
                    errors.append(f"[cases/{case_id}.json] Missing required top-level key '{req_key}'")

            # Check case sub-object
            c_obj = c_data.get("case")
            if not isinstance(c_obj, dict):
                errors.append(f"[cases/{case_id}.json] 'case' must be a dictionary")
            else:
                for req_sub_key in ["status", "verdict", "fraud_probability", "pattern", "pattern_description", "affected_txn_ids", "first_suspicious_txn_id", "connected_card_ids", "connected_device_profiles", "exposure_usd", "evidence", "similar_prior_cases", "summary", "written_to_graph", "graph_case_id"]:
                    if req_sub_key not in c_obj:
                        errors.append(f"[cases/{case_id}.json] case sub-object missing key '{req_sub_key}'")
                
                if not isinstance(c_obj.get("written_to_graph"), bool):
                    errors.append(f"[cases/{case_id}.json] case.written_to_graph must be a boolean")

                if c_obj.get("verdict") == Verdict.LEGITIMATE.value:
                    if float(c_obj.get("exposure_usd", -1)) != 0.0 or len(c_obj.get("affected_txn_ids", [1])) != 0:
                        errors.append(f"[cases/{case_id}.json] Legitimate case must have exposure_usd=0 and empty affected_txn_ids")

            # Check next_best_actions
            nba_obj = c_data.get("next_best_actions")
            if not isinstance(nba_obj, dict) or "initial" not in nba_obj or "final" not in nba_obj or "what_changed" not in nba_obj:
                errors.append(f"[cases/{case_id}.json] next_best_actions missing initial, final, or what_changed")
            else:
                for r in nba_obj.get("initial", []):
                    if r.get("action") not in VALID_ACTIONS or r.get("route") not in VALID_ROUTES:
                        errors.append(f"[cases/{case_id}.json] Invalid initial recommendation action/route: {r}")
                for r in nba_obj.get("final", []):
                    if r.get("action") not in VALID_ACTIONS or r.get("route") not in VALID_ROUTES:
                        errors.append(f"[cases/{case_id}.json] Invalid final recommendation action/route: {r}")

            # Check SAR
            sar_obj = c_data.get("sar")
            if not isinstance(sar_obj, dict) or "file" not in sar_obj or "reason" not in sar_obj:
                errors.append(f"[cases/{case_id}.json] sar missing file or reason")
            else:
                final_acts = {r.get("action") for r in (nba_obj.get("final", []) if isinstance(nba_obj, dict) else [])}
                file_rep = Action.FILE_REPORT.value in final_acts
                if sar_obj.get("file") is True:
                    if not file_rep:
                        errors.append(f"[cases/{case_id}.json] SAR file is True but FILE_REPORT not in final actions")
                    if not sar_obj.get("narrative") or len(sar_obj.get("narrative", "").strip()) < 20:
                        errors.append(f"[cases/{case_id}.json] SAR file is True but narrative missing/short")
                    if len(sar_obj.get("activity_dates", [])) != 2:
                        errors.append(f"[cases/{case_id}.json] SAR file is True but activity_dates length != 2")
                    if float(sar_obj.get("total_amount_usd", 0)) <= 0:
                        errors.append(f"[cases/{case_id}.json] SAR file is True but total_amount_usd <= 0")
                else:
                    if file_rep:
                        errors.append(f"[cases/{case_id}.json] FILE_REPORT in final actions but SAR file is False")
                    if sar_obj.get("narrative") or sar_obj.get("total_amount_usd", 0) != 0:
                        errors.append(f"[cases/{case_id}.json] Non-filed SAR must have empty narrative and 0 amount")

            # Check execution metadata
            if not isinstance(c_data.get("stop_reason"), str) or not c_data.get("stop_reason"):
                errors.append(f"[cases/{case_id}.json] Invalid or missing stop_reason")
            if not isinstance(c_data.get("tool_calls"), int) or c_data.get("tool_calls") < 0:
                errors.append(f"[cases/{case_id}.json] Invalid tool_calls")
            if not isinstance(c_data.get("tokens"), int) or c_data.get("tokens") < 0:
                errors.append(f"[cases/{case_id}.json] Invalid tokens")
            if not isinstance(c_data.get("latency_s"), (int, float)) or c_data.get("latency_s") < 0:
                errors.append(f"[cases/{case_id}.json] Invalid latency_s")

    if errors:
        print(f"Validation FAILED with {len(errors)} error(s):")
        for err in errors:
            print(f"  - {err}")
        return {"valid": False, "errors": errors}

    print("Benchmark Validation PASSED: All 20 cases and cases/*.json files are valid, conforming to Phase 3 contracts and official dataset schema.")
    return {"valid": True, "cases_count": 20, "errors": []}


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "outputs/benchmark_answers.json"
    result = validate_benchmark(target)
    sys.exit(0 if result["valid"] else 1)
