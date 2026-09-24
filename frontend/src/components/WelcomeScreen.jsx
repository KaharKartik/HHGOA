import React from 'react';

export function WelcomeScreen() {
  return (
    <div className="welcome-screen">
      <div style={{ fontSize: '36px', marginBottom: '12px' }}>🛡️</div>
      <div className="welcome-title">Select a Fraud Investigation Case</div>
      <div className="welcome-sub">
        Choose a benchmark case from the directory to review real graph evidence, policy engine R1–R10 execution, and automated decisioning.
      </div>
    </div>
  );
}
