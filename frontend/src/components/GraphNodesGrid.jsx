import React from 'react';

export function GraphNodesGrid({ data }) {
  if (!data) return null;

  // Extract actual data without placeholders
  const cardId =
    data.card_id ||
    data.connected_entities?.card_id ||
    data.details?.card_id ||
    data.case?.connected_card_ids?.[0] ||
    (data.evidence?.find((e) => e.fact && (e.fact.includes('Card') || e.fact.includes('-K'))))?.fact ||
    '—';

  const txnId =
    data.transaction_id ||
    data.flagged_transaction_id ||
    data.details?.transaction_id ||
    '—';

  const deviceProfile =
    data.device?.device_profile_id ||
    data.connected_entities?.device_profile_id ||
    data.case?.connected_device_profiles?.[0] ||
    (data.evidence?.find((e) => e.fact && (e.fact.includes('DP-') || e.fact.includes('DeviceProfile'))))?.fact ||
    'In-Person / Direct';

  const patternCluster = data.pattern
    ? data.pattern.replace(/_/g, ' ').toUpperCase()
    : data.case?.pattern
    ? data.case.pattern.replace(/_/g, ' ').toUpperCase()
    : data.billing_region
    ? `REGION ${data.billing_region}`
    : data.details?.billing_region
    ? `REGION ${data.details.billing_region}`
    : 'STANDARD FLOW';

  const customerId =
    data.customer_id ||
    data.connected_entities?.customer_id ||
    data.details?.customer_id ||
    data.case?.customer_id ||
    '—';

  const emailDomain =
    data.email_domain ||
    data.connected_entities?.email_domain ||
    data.details?.purchaser_email ||
    '—';

  return (
    <div className="panel-card">
      <div className="panel-header">
        <span className="panel-title">
          <span className="panel-title-icon">🕸️</span> Graph Connected Entities & Relationships
        </span>
      </div>
      <div className="panel-body">
        <div className="graph-nodes-grid">
          <div className="node-box">
            <div className="node-type">Card ID</div>
            <div className="node-id">{cardId}</div>
          </div>
          <div className="node-box">
            <div className="node-type">Transaction ID</div>
            <div className="node-id">{txnId}</div>
          </div>
          <div className="node-box">
            <div className="node-type">Customer ID</div>
            <div className="node-id">{customerId}</div>
          </div>
          <div className="node-box">
            <div className="node-type">Device Profile</div>
            <div className="node-id" style={{ fontSize: '11px' }}>
              {deviceProfile}
            </div>
          </div>
          <div className="node-box">
            <div className="node-type">Email Domain</div>
            <div className="node-id">{emailDomain}</div>
          </div>
          <div className="node-box">
            <div className="node-type">Pattern Cluster</div>
            <div className="node-id" style={{ color: 'var(--text-main)' }}>
              {patternCluster}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
