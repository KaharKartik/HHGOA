import React from 'react';

export function NextBestActionCard({ data }) {
  const nba = data.next_best_action || data.next_best_actions || {};
  const rationale = nba.what_changed || 'Standard policy progression executed without deviation.';

  return (
    <div className="panel-card">
      <div className="panel-header">
        <span className="panel-title">
          <span className="panel-title-icon">⚡</span> Next Best Action (NBA)
        </span>
      </div>
      <div className="panel-body">
        <div style={{ fontSize: '12px', color: 'var(--text-muted)', lineHeight: '1.6' }}>
          <strong style={{ color: 'var(--text-main)' }}>Transition Rationale:</strong>
          <br />
          {rationale}
        </div>
      </div>
    </div>
  );
}
