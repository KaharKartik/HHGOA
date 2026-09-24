import React from 'react';
import { getRouteClass } from '../utils/formatters';

export function FinalRecommendations({ data }) {
  const finalRecs = data.final_recommendations || data.next_best_action?.final || [];

  return (
    <div className="panel-card">
      <div className="panel-header">
        <span className="panel-title">
          <span className="panel-title-icon">✅</span> Final Action Recommendations
        </span>
      </div>
      <div className="panel-body">
        <div className="action-chip-list">
          {finalRecs.length > 0 ? (
            finalRecs.map((r, idx) => {
              const actionName = r.action || r;
              const route = r.route || 'AUTO';
              const routeClass = getRouteClass(route);

              return (
                <div key={idx} className="action-row" style={{ borderLeft: '3px solid var(--teal-primary)' }}>
                  <div>
                    <div className="action-name">{actionName}</div>
                    {r.reason && <div className="action-reason">{r.reason}</div>}
                  </div>
                  <span className={`route-badge ${routeClass}`}>{route}</span>
                </div>
              );
            })
          ) : (
            <div style={{ color: 'var(--text-dim)', fontSize: '12px' }}>
              No final recommendations.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
