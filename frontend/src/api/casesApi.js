const API = 'http://localhost:8000';

export async function fetchCases() {
  const r = await fetch(`${API}/cases`);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return await r.json();
}

export async function fetchCaseDetails(caseId) {
  const r = await fetch(`${API}/cases/${caseId}`);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return await r.json();
}

export async function searchTransactions(query, type = 'all', limit = 20) {
  const params = new URLSearchParams({ q: query, type, limit: String(limit) });
  const r = await fetch(`${API}/transactions/search?${params.toString()}`);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return await r.json();
}

export async function fetchTransactionDetails(transactionId) {
  const r = await fetch(`${API}/transactions/${encodeURIComponent(transactionId)}`);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return await r.json();
}

export function generateFallbackCases() {
  const ids = [
    "HHG-001","HHG-002","HHG-003","HHG-004","HHG-005",
    "HHG-006","HHG-007","HHG-008","HHG-009","HHG-010",
    "HHG-011","HHG-012","HHG-013","HHG-014","HHG-015",
    "HHG-016","HHG-017","HHG-018","HHG-019","HHG-020"
  ];
  return ids.map(id => ({
    case_id: id,
    flagged_txn_id: "35" + Math.floor(10000 + Math.random() * 90000),
    verdict: null,
    trigger_type: "risk_score"
  }));
}
