import React from 'react';

export function ProgressionTimeline({ data }) {
  const verdict = (data.verdict || 'UNCERTAIN').toUpperCase();
  const evidenceCount = (data.evidence || data.case?.evidence || []).length;
  const explanation = data.explanation || data.case?.summary || 'Policy rules applied cleanly.';
  const flaggedTxn = data.flagged_transaction_id || '';

  return (
    <div className="panel-card">
      <div className="panel-header">
        <span className="panel-title">
          <span className="panel-title-icon">⏱️</span> Investigation Progression & Audit Trail
        </span>
      </div>
      <div className="panel-body">
        <div className="timeline">
          <div className="timeline-item">
            <div className="timeline-step">Step 1 · Risk Trigger Ingestion</div>
            <div className="timeline-title">Flagged Transaction {flaggedTxn}</div>
            <div className="timeline-desc">
              Initial alert evaluated from case pack trigger data. Customer context retrieved.
            </div>
          </div>
          <div className="timeline-item">
            <div className="timeline-step">Step 2 · TigerGraph 1-Hop & Sequence Traversal</div>
            <div className="timeline-title">Graph Evidence Collected ({evidenceCount} facts)</div>
            <div className="timeline-desc">
              Analyzed device profiles, billing regions, email domains, and prior closed case history.
            </div>
          </div>
          <div className={`timeline-item ${verdict === 'FRAUD' ? 'fraud-node' : ''}`}>
            <div className="timeline-step">Step 3 · R1–R10 Policy Engine & SAR Evaluation</div>
            <div className="timeline-title">Verdict Reached: {verdict}</div>
            <div className="timeline-desc">{explanation}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
