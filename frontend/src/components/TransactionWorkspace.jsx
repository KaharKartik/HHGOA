import React from 'react';
import { fmtMoney } from '../utils/formatters';
import { GraphNodesGrid } from './GraphNodesGrid';

export function TransactionWorkspace({
  data,
  isLoading,
  error,
  onOpenCase,
}) {
  if (isLoading) {
    return (
      <main className="workspace" id="workspaceArea">
        <div style={{ padding: '28px' }}>
          <div className="skeleton-box" style={{ height: '80px', marginBottom: '20px' }}></div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: '20px' }}>
            <div>
              <div className="skeleton-box" style={{ height: '140px', marginBottom: '16px' }}></div>
              <div className="skeleton-box" style={{ height: '220px', marginBottom: '16px' }}></div>
            </div>
            <div>
              <div className="skeleton-box" style={{ height: '180px', marginBottom: '16px' }}></div>
              <div className="skeleton-box" style={{ height: '240px', marginBottom: '16px' }}></div>
            </div>
          </div>
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="workspace" id="workspaceArea">
        <div style={{ padding: '40px' }}>
          <div className="panel-card" style={{ borderColor: 'var(--fraud-border)' }}>
            <div className="panel-header">
              <span className="panel-title" style={{ color: 'var(--fraud-red)' }}>
                ⚠️ Transaction Query Error
              </span>
            </div>
            <div className="panel-body" style={{ color: 'var(--text-muted)', fontSize: '13px' }}>
              Failed to query transaction details from TigerGraph: {error}
            </div>
          </div>
        </div>
      </main>
    );
  }

  if (!data) return null;

  const details = data.details || {};
  const device = data.device || {};
  const customerContext = data.customer_context || {};
  const priorCases = data.prior_cases || [];
  const sequence = data.sequence || [];
  const latency = data.latency_ms ? `${data.latency_ms.toFixed(1)}ms` : '320ms';

  const amount = details.amount != null ? details.amount : 0;
  const channel = details.channel || '—';
  const region = details.billing_region || '—';
  const email = details.purchaser_email || data.email_domain || '—';

  // Find if this transaction or customer links to an active benchmark case
  const activeCase = priorCases.find(
    (c) => c.status === 'active_investigation' && c.case_id?.startsWith('HHG')
  );

  return (
    <main className="workspace" id="workspaceArea">
      {/* Live Transaction Header */}
      <div className="case-header">
        <div className="case-header-main">
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <span className="header-case-id" style={{ color: 'var(--teal-accent)' }}>
                TXN {data.transaction_id}
              </span>
              <span
                className="case-row-badge badge-legit"
                style={{ fontSize: '10px', padding: '3px 8px' }}
              >
                LIVE GRAPH NODE
              </span>
              {activeCase && (
                <button
                  className="quick-link-btn"
                  onClick={() => onOpenCase && onOpenCase(activeCase.case_id)}
                  style={{
                    background: 'var(--teal-bg)',
                    border: '1px solid var(--teal-primary)',
                    color: 'var(--teal-accent)',
                    padding: '3px 10px',
                    borderRadius: '4px',
                    fontSize: '11px',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  🔗 Linked Case: {activeCase.case_id}
                </button>
              )}
            </div>

            <div className="header-meta-list">
              <div className="header-meta-item">
                <span className="header-meta-label">Customer:</span>
                <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-main)' }}>
                  {details.customer_id || '—'}
                </span>
              </div>
              <div className="header-meta-item">
                <span className="header-meta-label">Card:</span>
                <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-main)' }}>
                  {details.card_id || '—'}
                </span>
              </div>
              <div className="header-meta-item">
                <span className="header-meta-label">Channel:</span>
                <span style={{ textTransform: 'capitalize' }}>{channel.replace('_', ' ')}</span>
              </div>
              <div className="header-meta-item">
                <span className="header-meta-label">Timestamp:</span>
                <span style={{ fontFamily: 'var(--font-mono)' }}>{details.ts || '—'}</span>
              </div>
              <div className="header-meta-item">
                <span className="header-meta-label">Query Latency:</span>
                <span style={{ color: 'var(--teal-accent)', fontFamily: 'var(--font-mono)' }}>
                  ⚡ {latency}
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="header-kpi-row">
          <div className="kpi-block">
            <div className="kpi-label">Amount USD</div>
            <div className="kpi-value" style={{ color: 'var(--text-main)' }}>
              {fmtMoney(amount)}
            </div>
          </div>
          <div className="kpi-block">
            <div className="kpi-label">Billing Region</div>
            <div className="kpi-value" style={{ color: 'var(--teal-accent)' }}>
              {region}
            </div>
          </div>
          <div className="kpi-block">
            <div className="kpi-label">Prior Cases</div>
            <div
              className="kpi-value"
              style={{ color: priorCases.length > 0 ? 'var(--uncertain-amber)' : 'var(--legit-green)' }}
            >
              {priorCases.length}
            </div>
          </div>
        </div>
      </div>

      {/* Main Content Layout */}
      <div className="workspace-content">
        {/* Left Column */}
        <div>
          {/* Graph Relationship Grid */}
          <GraphNodesGrid data={data} />

          {/* Dynamic Transaction Attributes */}
          <div className="panel-card">
            <div className="panel-header">
              <span className="panel-title">
                <span className="panel-title-icon">📊</span> Transaction Telemetry & Graph Attributes
              </span>
            </div>
            <div className="panel-body">
              <table className="evidence-table">
                <thead>
                  <tr>
                    <th>Attribute</th>
                    <th>Graph Value</th>
                    <th>Edge Type / Source</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td style={{ fontWeight: 600, color: 'var(--text-main)' }}>Transaction ID</td>
                    <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--teal-accent)' }}>
                      {data.transaction_id}
                    </td>
                    <td><span className="source-tag source-graph">VERTEX: Transaction</span></td>
                  </tr>
                  <tr>
                    <td style={{ fontWeight: 600, color: 'var(--text-main)' }}>Customer ID</td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>{details.customer_id || '—'}</td>
                    <td><span className="source-tag source-graph">MADE_BY Customer</span></td>
                  </tr>
                  <tr>
                    <td style={{ fontWeight: 600, color: 'var(--text-main)' }}>Card ID</td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>{details.card_id || '—'}</td>
                    <td><span className="source-tag source-graph">MADE on Card</span></td>
                  </tr>
                  <tr>
                    <td style={{ fontWeight: 600, color: 'var(--text-main)' }}>Amount (USD)</td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>{fmtMoney(amount)}</td>
                    <td><span className="source-tag source-graph">ATTRIB: amount</span></td>
                  </tr>
                  <tr>
                    <td style={{ fontWeight: 600, color: 'var(--text-main)' }}>Channel</td>
                    <td style={{ textTransform: 'capitalize' }}>{channel}</td>
                    <td><span className="source-tag source-graph">ATTRIB: channel</span></td>
                  </tr>
                  <tr>
                    <td style={{ fontWeight: 600, color: 'var(--text-main)' }}>Product Code</td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>{details.product_cd || '—'}</td>
                    <td><span className="source-tag source-graph">ATTRIB: product_cd</span></td>
                  </tr>
                  <tr>
                    <td style={{ fontWeight: 600, color: 'var(--text-main)' }}>Billing Region</td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>{region}</td>
                    <td><span className="source-tag source-graph">BILLED_IN BillingRegion</span></td>
                  </tr>
                  <tr>
                    <td style={{ fontWeight: 600, color: 'var(--text-main)' }}>Purchaser Email</td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>{email}</td>
                    <td><span className="source-tag source-graph">PURCHASER_EMAIL EmailDomain</span></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          {/* Device Profile Card */}
          <div className="panel-card">
            <div className="panel-header">
              <span className="panel-title">
                <span className="panel-title-icon">📱</span> Connected Device Profile & Fingerprint
              </span>
            </div>
            <div className="panel-body">
              {device && (device.device_profile_id || device.device_info) ? (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '10px' }}>
                  <div className="node-box">
                    <div className="node-type">Profile ID</div>
                    <div className="node-id" style={{ fontSize: '11px' }}>{device.device_profile_id || '—'}</div>
                  </div>
                  <div className="node-box">
                    <div className="node-type">Device Info</div>
                    <div className="node-id" style={{ color: 'var(--text-main)' }}>{device.device_info || '—'}</div>
                  </div>
                  <div className="node-box">
                    <div className="node-type">Operating System</div>
                    <div className="node-id" style={{ color: 'var(--text-main)' }}>{device.os || '—'}</div>
                  </div>
                  <div className="node-box">
                    <div className="node-type">Browser</div>
                    <div className="node-id" style={{ color: 'var(--text-main)' }}>{device.browser || '—'}</div>
                  </div>
                  <div className="node-box">
                    <div className="node-type">Screen Resolution</div>
                    <div className="node-id" style={{ color: 'var(--text-main)' }}>{device.screen || '—'}</div>
                  </div>
                  <div className="node-box">
                    <div className="node-type">Device Type</div>
                    <div className="node-id" style={{ color: 'var(--text-main)', textTransform: 'capitalize' }}>
                      {device.device_type || '—'}
                    </div>
                  </div>
                </div>
              ) : (
                <div style={{ color: 'var(--text-dim)', fontSize: '12px', padding: '6px 0' }}>
                  No digital device profile associated (in-person point of sale or direct batch transaction).
                </div>
              )}
            </div>
          </div>

          {/* Sequence Traversal */}
          {sequence.length > 0 && (
            <div className="panel-card">
              <div className="panel-header">
                <span className="panel-title">
                  <span className="panel-title-icon">➡️</span> Subsequent Transaction Sequence (NEXT Edges)
                </span>
              </div>
              <div className="panel-body">
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  {sequence.map((s, idx) => (
                    <span key={idx} className="entity-pill" style={{ color: 'var(--teal-accent)' }}>
                      NEXT → {s.transaction_id}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right Column */}
        <div>
          {/* Customer History Context */}
          <div className="panel-card">
            <div className="panel-header">
              <span className="panel-title">
                <span className="panel-title-icon">👤</span> Customer Profile & Graph History
              </span>
            </div>
            <div className="panel-body">
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div className="action-row">
                  <div>
                    <div className="action-name">Customer ID</div>
                    <div className="action-reason">{details.customer_id || '—'}</div>
                  </div>
                  <span className="route-badge route-auto">VERIFIED</span>
                </div>
                <div className="action-row">
                  <div>
                    <div className="action-name">Active Card</div>
                    <div className="action-reason">{details.card_id || '—'}</div>
                  </div>
                  <span className="route-badge route-l1">LINKED</span>
                </div>
                <div className="action-row">
                  <div>
                    <div className="action-name">Historical Closed Cases</div>
                    <div className="action-reason">
                      {customerContext.total_prior_cases || priorCases.length} incidents on file
                    </div>
                  </div>
                  <span
                    className={`route-badge ${
                      priorCases.length > 0 ? 'route-l2' : 'route-auto'
                    }`}
                  >
                    {priorCases.length > 0 ? 'RISK HISTORY' : 'CLEAN RECORD'}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Connected Prior Cases */}
          <div className="panel-card">
            <div className="panel-header">
              <span className="panel-title">
                <span className="panel-title-icon">📁</span> Prior Cases & Incident History
              </span>
              <span style={{ fontSize: '11px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                {priorCases.length} Cases
              </span>
            </div>
            <div className="panel-body">
              {priorCases.length === 0 ? (
                <div style={{ color: 'var(--text-dim)', fontSize: '12px' }}>
                  No prior cases or fraud reports associated with this card or customer.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {priorCases.map((c, i) => (
                    <div key={i} className="action-row" style={{ alignItems: 'flex-start' }}>
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span className="action-name" style={{ color: 'var(--teal-accent)' }}>
                            {c.case_id}
                          </span>
                          {c.outcome && (
                            <span
                              className={`case-row-badge ${
                                c.outcome === 'confirmed_fraud' ? 'badge-fraud' : 'badge-legit'
                              }`}
                              style={{ fontSize: '9px', padding: '1px 5px' }}
                            >
                              {c.outcome.replace('_', ' ')}
                            </span>
                          )}
                        </div>
                        <div className="action-reason" style={{ marginTop: '3px' }}>
                          {c.pattern ? `Pattern: ${c.pattern.replace(/_/g, ' ')}` : c.trigger_text || 'Prior case'}
                        </div>
                        {c.exposure_usd != null && (
                          <div style={{ fontSize: '11px', color: 'var(--fraud-red)', marginTop: '2px', fontFamily: 'var(--font-mono)' }}>
                            Exposure: {fmtMoney(c.exposure_usd)}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* If linked to Benchmark Case, CTA */}
          {activeCase && (
            <div className="sar-panel" style={{ marginTop: '16px' }}>
              <div className="sar-header">
                <span className="sar-badge">Benchmark Pack Available</span>
                <span className="sar-amount">{activeCase.case_id}</span>
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '12px', lineHeight: 1.5 }}>
                This transaction is the flagged trigger for benchmark case {activeCase.case_id}. Open the complete investigation to inspect the multi-hop policy traces, uncertainty evaluation, and SAR filing decisions.
              </div>
              <button
                onClick={() => onOpenCase && onOpenCase(activeCase.case_id)}
                style={{
                  width: '100%',
                  background: 'var(--teal-primary)',
                  color: '#fff',
                  border: 'none',
                  padding: '9px 14px',
                  borderRadius: '4px',
                  fontSize: '12px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px',
                }}
              >
                🔬 Open Full Case Investigation ({activeCase.case_id})
              </button>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
