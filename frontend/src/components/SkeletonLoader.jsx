import React from 'react';

export function SkeletonLoader({ caseId }) {
  return (
    <>
      <div className="case-header">
        <div className="case-header-main">
          <div>
            <div className="header-case-id">Case {caseId}</div>
            <div style={{ color: 'var(--text-muted)', fontSize: '12px', marginTop: '4px' }}>
              Executing TigerGraph GSQL queries & R1–R10 policy engine…
            </div>
          </div>
        </div>
      </div>
      <div className="workspace-content">
        <div>
          <div className="panel-card">
            <div className="panel-body">
              <div className="skeleton-box" style={{ height: '140px' }}></div>
            </div>
          </div>
          <div className="panel-card">
            <div className="panel-body">
              <div className="skeleton-box" style={{ height: '200px' }}></div>
            </div>
          </div>
        </div>
        <div>
          <div className="panel-card">
            <div className="panel-body">
              <div className="skeleton-box" style={{ height: '280px' }}></div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
