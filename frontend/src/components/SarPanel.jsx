import React from 'react';
import { fmtMoney } from '../utils/formatters';

export function SarPanel({ data }) {
  const exposure = data.case?.exposure_usd ?? 0;
  const sar = data.sar_decision || data.sar || {};
  const sarFiled = sar.file === true;
  const amount = fmtMoney(sar.total_amount_usd || exposure);

  return (
    <div className="sar-panel">
      <div className="sar-header">
        <span className="sar-badge">
          {sarFiled ? '🚨 SAR Filing Triggered' : '✓ SAR Cleared'}
        </span>
        <span className="sar-amount">{amount}</span>
      </div>
      {sarFiled ? (
        <div className="sar-narrative">
          {sar.narrative || sar.reason || 'SAR filed per regulatory policy thresholds.'}
        </div>
      ) : (
        <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
          {sar.reason || 'Exposure and risk score below SAR threshold.'}
        </div>
      )}
    </div>
  );
}
