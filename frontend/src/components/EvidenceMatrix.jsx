import React from 'react';

export function EvidenceMatrix({ data }) {
  const evidence = data.evidence || data.case?.evidence || [];

  return (
    <div className="panel-card">
      <div className="panel-header">
        <span className="panel-title">
          <span className="panel-title-icon">🔍</span> Traceable Evidence Matrix ({evidence.length})
        </span>
      </div>
      <div className="panel-body" style={{ padding: 0 }}>
        {evidence.length > 0 ? (
          <table className="evidence-table">
            <thead>
              <tr>
                <th style={{ width: '90px' }}>Source</th>
                <th>Claim / Finding</th>
                <th>Reference</th>
                <th>Traceable Entity IDs</th>
              </tr>
            </thead>
            <tbody>
              {evidence.map((ev, idx) => {
                const source = (ev.source || 'GRAPH').toUpperCase();
                const sourceClass = `source-${source.toLowerCase()}`;

                return (
                  <tr key={idx}>
                    <td>
                      <span className={`source-tag ${sourceClass}`}>{source}</span>
                    </td>
                    <td style={{ color: 'var(--text-main)', fontWeight: 500 }}>
                      {ev.claim || ''}
                    </td>
                    <td>
                      <code style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-dim)' }}>
                        {ev.ref || '—'}
                      </code>
                    </td>
                    <td>
                      {(ev.entity_ids || []).length > 0
                        ? ev.entity_ids.map((eid, eidx) => (
                            <span key={eidx} className="entity-pill">
                              {eid}
                            </span>
                          ))
                        : '—'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        ) : (
          <div style={{ padding: '18px', color: 'var(--text-dim)' }}>
            No specific evidence items returned.
          </div>
        )}
      </div>
    </div>
  );
}
