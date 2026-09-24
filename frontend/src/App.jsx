import React from 'react';
import { useCases } from './state/useCases';
import { Sidebar } from './components/Sidebar';
import { Workspace } from './components/Workspace';
import './styles/main.css';

export function App() {
  const {
    activeId,
    activeCaseData,
    isLoadingDetails,
    detailError,
    isOnline,
    statusText,
    searchQuery,
    setSearchQuery,
    currentFilter,
    setCurrentFilter,
    selectCase,
    counts,
    filteredCases,

    // Live investigation props
    activeMode,
    setActiveMode,
    globalQuery,
    setGlobalQuery,
    searchType,
    setSearchType,
    isSearching,
    searchResults,
    searchLatency,
    searchError,
    executeSearch,
    selectedTxnId,
    activeTxnData,
    isLoadingTxn,
    txnError,
    selectTransaction,
  } = useCases();

  return (
    <div className="app-shell">
      <Sidebar
        activeId={activeId}
        isOnline={isOnline}
        statusText={statusText}
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
        currentFilter={currentFilter}
        setCurrentFilter={setCurrentFilter}
        selectCase={selectCase}
        counts={counts}
        filteredCases={filteredCases}
        activeMode={activeMode}
        setActiveMode={setActiveMode}
        globalQuery={globalQuery}
        setGlobalQuery={setGlobalQuery}
        searchType={searchType}
        setSearchType={setSearchType}
        isSearching={isSearching}
        searchResults={searchResults}
        searchLatency={searchLatency}
        searchError={searchError}
        executeSearch={executeSearch}
        selectedTxnId={selectedTxnId}
        selectTransaction={selectTransaction}
      />
      <Workspace
        activeId={activeId}
        activeCaseData={activeCaseData}
        isLoadingDetails={isLoadingDetails}
        detailError={detailError}
        selectedTxnId={selectedTxnId}
        activeTxnData={activeTxnData}
        isLoadingTxn={isLoadingTxn}
        txnError={txnError}
        onOpenCase={(caseId) => {
          setActiveMode('queue');
          selectCase(caseId);
        }}
      />
    </div>
  );
}

export default App;
