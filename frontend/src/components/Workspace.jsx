import React from 'react';
import { WelcomeScreen } from './WelcomeScreen';
import { SkeletonLoader } from './SkeletonLoader';
import { CaseHeader } from './CaseHeader';
import { ProgressionTimeline } from './ProgressionTimeline';
import { GraphNodesGrid } from './GraphNodesGrid';
import { EvidenceMatrix } from './EvidenceMatrix';
import { PolicyTraces } from './PolicyTraces';
import { InitialRecommendations } from './InitialRecommendations';
import { FinalRecommendations } from './FinalRecommendations';
import { NextBestActionCard } from './NextBestActionCard';
import { SarPanel } from './SarPanel';
import { TransactionWorkspace } from './TransactionWorkspace';

export function Workspace({
  activeId,
  activeCaseData,
  isLoadingDetails,
  detailError,
  selectedTxnId,
  activeTxnData,
  isLoadingTxn,
  txnError,
  onOpenCase,
}) {
  // If a live transaction is selected, render TransactionWorkspace
  if (selectedTxnId) {
    return (
      <TransactionWorkspace
        data={activeTxnData}
        isLoading={isLoadingTxn}
        error={txnError}
        onOpenCase={onOpenCase}
      />
    );
  }

  // If no case and no transaction is selected
  if (!activeId) {
    return (
      <main className="workspace" id="workspaceArea">
        <WelcomeScreen />
      </main>
    );
  }

  if (isLoadingDetails) {
    return (
      <main className="workspace" id="workspaceArea">
        <SkeletonLoader caseId={activeId} />
      </main>
    );
  }

  if (detailError) {
    return (
      <main className="workspace" id="workspaceArea">
        <div style={{ padding: '40px' }}>
          <div className="panel-card" style={{ borderColor: 'var(--fraud-border)' }}>
            <div className="panel-header">
              <span className="panel-title" style={{ color: 'var(--fraud-red)' }}>
                ⚠️ Error Loading Case {activeId}
              </span>
            </div>
            <div className="panel-body" style={{ color: 'var(--text-muted)', fontSize: '13px' }}>
              Failed to retrieve case details from endpoint: {detailError}
            </div>
          </div>
        </div>
      </main>
    );
  }

  if (!activeCaseData) {
    return null;
  }

  return (
    <main className="workspace" id="workspaceArea">
      <CaseHeader caseId={activeId} data={activeCaseData} />

      <div className="workspace-content">
        {/* Left Column (Evidence & Timeline) */}
        <div>
          <ProgressionTimeline data={activeCaseData} />
          <GraphNodesGrid data={activeCaseData} />
          <EvidenceMatrix data={activeCaseData} />
          <PolicyTraces data={activeCaseData} />
        </div>

        {/* Right Column (Decisioning & SAR) */}
        <div>
          <InitialRecommendations data={activeCaseData} />
          <FinalRecommendations data={activeCaseData} />
          <NextBestActionCard data={activeCaseData} />
          <SarPanel data={activeCaseData} />
        </div>
      </div>
    </main>
  );
}
