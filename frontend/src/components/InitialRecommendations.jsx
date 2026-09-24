import React from 'react';
import { getRouteClass } from '../utils/formatters';

export function InitialRecommendations({ data }) {
  const initRecs = data.initial_recommendations || data.next_best_action?.initial || [];

  return (
    <div className="panel-card">
      <div className="panel-header">
        <span className="panel-title">
          <span className="panel-title-icon">📥</span> Initial Action Recommendations
        </span>
      </div>
      <div className="panel-body">
        <div className="action-chip-list">
          {initRecs.length > 0 ? (
            initRecs.map((r, idx) => {
              const actionName = r.action || r;
              const route = r.route || 'AUTO';
              const routeClass = getRouteClass(route);

              return (
                <div key={idx} className="action-row">
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
              No initial recommendations.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
