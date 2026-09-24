import React from 'react';
import { fmtMoney, fmtProb, getVerdictClass } from '../utils/formatters';

export function CaseHeader({ caseId, data }) {
  const verdict = (data.verdict || 'UNCERTAIN').toUpperCase();
  const verdictBadgeClass = getVerdictClass(verdict);
  const prob = data.fraud_probability ?? 0;
  const uncertainty = data.uncertainty ?? 0;
  const exposure = data.case?.exposure_usd ?? 0;
  const pattern = data.pattern || data.case?.pattern || 'none';
  const latency = data.latency_s ? data.latency_s.toFixed(2) + 's' : '0.45s';

  const probColor =
    verdict === 'FRAUD'
      ? 'var(--fraud-red)'
      : verdict === 'LEGITIMATE'
      ? 'var(--legit-green)'
      : 'var(--uncertain-amber)';

  const exposureColor = exposure > 0 ? 'var(--fraud-red)' : 'var(--legit-green)';

  return (
    <div className="case-header">
      <div className="case-header-main">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span className="header-case-id">{caseId}</span>
            <span
              className={`case-row-badge ${verdictBadgeClass}`}
              style={{ fontSize: '11px', padding: '4px 10px' }}
            >
              {verdict}
            </span>
          </div>
          <div className="header-meta-list">
            <div className="header-meta-item">
              <span className="header-meta-label">Flagged Txn:</span>
              <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--teal-accent)' }}>
                {data.flagged_transaction_id || '—'}
              </span>
            </div>
            <div className="header-meta-item">
              <span className="header-meta-label">Pattern:</span>
              <span style={{ fontFamily: 'var(--font-mono)' }}>
                {pattern.replace(/_/g, ' ')}
              </span>
            </div>
            <div className="header-meta-item">
              <span className="header-meta-label">Latency:</span>
              <span>{latency}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="header-kpi-row">
        <div className="kpi-block">
          <div className="kpi-label">Fraud Probability</div>
          <div className="kpi-value" style={{ color: probColor }}>
            {fmtProb(prob)}
          </div>
        </div>
        <div className="kpi-block">
          <div className="kpi-label">Uncertainty</div>
          <div className="kpi-value" style={{ color: 'var(--text-muted)' }}>
            {uncertainty.toFixed(2)}
          </div>
        </div>
        <div className="kpi-block">
          <div className="kpi-label">Exposure USD</div>
          <div className="kpi-value" style={{ color: exposureColor }}>
            {fmtMoney(exposure)}
          </div>
        </div>
      </div>
    </div>
  );
}
