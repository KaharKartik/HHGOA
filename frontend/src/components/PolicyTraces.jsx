import React from 'react';

export function PolicyTraces({ data }) {
  const explanation = data.explanation || 'Rule set evaluated without policy violations.';

  return (
    <div className="panel-card">
      <div className="panel-header">
        <span className="panel-title">
          <span className="panel-title-icon">📜</span> R1–R10 Policy Evidence Chunks
        </span>
      </div>
      <div className="panel-body">
        <div className="policy-chunk">
          <div className="policy-chunk-header">R1–R10 Policy Engine Match</div>
          <div className="policy-chunk-text">{explanation}</div>
        </div>
      </div>
    </div>
  );
}
