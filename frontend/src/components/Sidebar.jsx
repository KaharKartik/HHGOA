import React from 'react';
import { getVerdictClass, fmtMoney } from '../utils/formatters';

export function Sidebar({
  activeId,
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
  selectTransaction,
}) {
  const handleLiveSearchSubmit = (e) => {
    e.preventDefault();
    executeSearch(globalQuery, searchType);
  };

  const handleQuickSample = (sampleText, sampleType) => {
    setGlobalQuery(sampleText);
    setSearchType(sampleType);
    executeSearch(sampleText, sampleType);
  };

  return (
    <aside className="sidebar">
      {/* Brand & Connection Status */}
      <div className="sidebar-brand">
        <div className="brand-title-wrap">
          <div className="brand-mark"></div>
          <div>
            <div className="brand-title">HH Goa · Fraud Intel</div>
            <div className="brand-subtitle">Enterprise Investigation</div>
          </div>
        </div>
        <div className="status-pill">
          <div className={`status-dot ${!isOnline ? 'offline' : ''}`}></div>
          <span>{statusText}</span>
        </div>
      </div>

      {/* Mode Switcher Tabs */}
      <div className="sidebar-mode-nav">
        <button
          className={`mode-nav-btn ${activeMode === 'queue' ? 'active' : ''}`}
          onClick={() => setActiveMode('queue')}
        >
          📁 Benchmark Queue ({counts.all})
        </button>
        <button
          className={`mode-nav-btn ${activeMode === 'live' ? 'active' : ''}`}
          onClick={() => setActiveMode('live')}
        >
          ⚡ Live Graph Search
        </button>
      </div>

      {/* Mode 1: Benchmark Queue */}
      {activeMode === 'queue' && (
        <>
          <div className="sidebar-controls">
            <div className="search-input-wrap">
              <span className="search-icon">🔍</span>
              <input
                type="text"
                className="search-input"
                placeholder="Filter Case or Txn ID…"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            <div className="filter-tabs">
              <button
                className={`filter-tab ${currentFilter === 'all' ? 'active' : ''}`}
                onClick={() => setCurrentFilter('all')}
              >
                All (<span>{counts.all}</span>)
              </button>
              <button
                className={`filter-tab ${currentFilter === 'fraud' ? 'active' : ''}`}
                onClick={() => setCurrentFilter('fraud')}
              >
                Fraud (<span>{counts.fraud}</span>)
              </button>
              <button
                className={`filter-tab ${currentFilter === 'legit' ? 'active' : ''}`}
                onClick={() => setCurrentFilter('legit')}
              >
                Legit (<span>{counts.legit}</span>)
              </button>
              <button
                className={`filter-tab ${currentFilter === 'uncertain' ? 'active' : ''}`}
                onClick={() => setCurrentFilter('uncertain')}
              >
                Uncertain (<span>{counts.uncertain}</span>)
              </button>
            </div>
          </div>

          <div className="case-list-header">
            <span>Investigation Pack</span>
            <span>{counts.all} CASES</span>
          </div>

          <div className="case-list">
            {filteredCases.length === 0 ? (
              <div style={{ padding: '24px 16px', color: 'var(--text-dim)', textAlign: 'center', fontSize: '12px' }}>
                <p style={{ marginBottom: '10px' }}>No matching benchmark cases.</p>
                {searchQuery.trim() && (
                  <button
                    className="mode-nav-btn active"
                    style={{ fontSize: '11px', padding: '6px 12px', margin: '0 auto' }}
                    onClick={() => {
                      setActiveMode('live');
                      setGlobalQuery(searchQuery);
                      executeSearch(searchQuery, 'all');
                    }}
                  >
                    ⚡ Search "{searchQuery}" in Live Graph →
                  </button>
                )}
              </div>
            ) : (
              filteredCases.map((c) => {
                const verdict = c.verdict;
                const badgeText = (verdict || 'PENDING').toUpperCase();
                const badgeClass = getVerdictClass(verdict);
                const txnId = c.flagged_txn_id || c.flagged_transaction_id || '—';

                return (
                  <div
                    key={c.case_id}
                    className={`case-row ${c.case_id === activeId ? 'active' : ''}`}
                    onClick={() => selectCase(c.case_id)}
                  >
                    <div className="case-row-id">{c.case_id}</div>
                    <div className={`case-row-badge ${badgeClass}`}>{badgeText}</div>
                    <div className="case-row-txn">Txn: {txnId}</div>
                  </div>
                );
              })
            )}
          </div>
        </>
      )}

      {/* Mode 2: Live Graph Search */}
      {activeMode === 'live' && (
        <>
          <div className="sidebar-controls">
            <form onSubmit={handleLiveSearchSubmit}>
              {/* Search Type Selector */}
              <div className="search-type-chips">
                {[
                  { id: 'all', label: 'All Entities' },
                  { id: 'transaction', label: 'Txn' },
                  { id: 'customer', label: 'Customer' },
                  { id: 'card', label: 'Card' },
                  { id: 'device', label: 'Device' },
                ].map((t) => (
                  <button
                    key={t.id}
                    type="button"
                    className={`type-chip ${searchType === t.id ? 'active' : ''}`}
                    onClick={() => {
                      setSearchType(t.id);
                      if (globalQuery.trim()) {
                        executeSearch(globalQuery, t.id);
                      }
                    }}
                  >
                    {t.label}
                  </button>
                ))}
              </div>

              {/* Global Search Input */}
              <div className="search-input-wrap" style={{ marginTop: '8px' }}>
                <span className="search-icon">⚡</span>
                <input
                  type="text"
                  className="search-input"
                  placeholder="Txn ID, Customer, Card, or Device…"
                  value={globalQuery}
                  onChange={(e) => setGlobalQuery(e.target.value)}
                />
              </div>

              <div style={{ display: 'flex', gap: '6px', marginTop: '8px' }}>
                <button
                  type="submit"
                  disabled={isSearching}
                  style={{
                    flex: 1,
                    background: 'var(--teal-primary)',
                    color: '#fff',
                    border: 'none',
                    padding: '6px 12px',
                    borderRadius: '4px',
                    fontSize: '11px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '6px',
                  }}
                >
                  {isSearching ? 'Querying Savanna…' : '🔍 Execute Graph Query'}
                </button>
              </div>
            </form>

            {/* Quick Sample Queries */}
            <div style={{ marginTop: '6px' }}>
              <div style={{ fontSize: '10px', color: 'var(--text-dim)', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Sample Graph Queries:
              </div>
              <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                {[
                  { q: '3514030', t: 'transaction', label: 'Txn 3514030' },
                  { q: '3015439', t: 'transaction', label: 'Txn 3015439' },
                  { q: 'C12382', t: 'customer', label: 'Cust C12382' },
                  { q: 'C12382-K1', t: 'card', label: 'Card C12382-K1' },
                  { q: 'DP-6c62ee8f8ddc524430f7834b', t: 'device', label: 'Device DP-6c' },
                ].map((s, idx) => (
                  <button
                    key={idx}
                    type="button"
                    className="quick-sample-chip"
                    onClick={() => handleQuickSample(s.q, s.t)}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Results Status Header */}
          <div className="case-list-header">
            <span>
              {isSearching
                ? 'Querying Graph…'
                : searchResults.length > 0
                ? `${searchResults.length} Graph Matches`
                : 'Live Results'}
            </span>
            {searchLatency != null && (
              <span style={{ color: 'var(--teal-accent)', fontFamily: 'var(--font-mono)' }}>
                ⚡ {searchLatency}ms
              </span>
            )}
          </div>

          {/* Live Search Results List */}
          <div className="case-list">
            {isSearching ? (
              <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '12px' }}>
                <div className="skeleton-box" style={{ height: '50px', marginBottom: '8px' }}></div>
                <div className="skeleton-box" style={{ height: '50px', marginBottom: '8px' }}></div>
                <div className="skeleton-box" style={{ height: '50px' }}></div>
              </div>
            ) : searchError ? (
              <div style={{ padding: '20px', color: 'var(--fraud-red)', fontSize: '12px', textAlign: 'center' }}>
                ⚠️ {searchError}
              </div>
            ) : searchResults.length === 0 ? (
              <div style={{ padding: '30px 16px', color: 'var(--text-dim)', textAlign: 'center', fontSize: '12px', lineHeight: 1.6 }}>
                {globalQuery.trim()
                  ? 'No matching graph nodes found. Try searching a transaction ID (e.g. 3514030) or customer ID (e.g. C12382).'
                  : 'Enter a transaction ID, customer ID, card ID, or device profile ID to query live TigerGraph Savanna.'}
              </div>
            ) : (
              searchResults.map((item) => {
                const isSelected = item.transaction_id === selectedTxnId;
                const matchTag = item.matched_by ? item.matched_by.replace('_', ' ').toUpperCase() : 'MATCH';

                return (
                  <div
                    key={item.transaction_id}
                    className={`case-row ${isSelected ? 'active' : ''}`}
                    onClick={() => selectTransaction(item.transaction_id)}
                    style={{ gridTemplateColumns: '1fr auto' }}
                  >
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span className="case-row-id">TXN {item.transaction_id}</span>
                        {item.associated_case_id && (
                          <span
                            className="case-row-badge badge-pending"
                            style={{ fontSize: '9px', padding: '1px 5px' }}
                          >
                            {item.associated_case_id}
                          </span>
                        )}
                      </div>
                      <div className="case-row-txn" style={{ marginTop: '2px' }}>
                        {item.customer_id ? `Cust: ${item.customer_id}` : ''}
                        {item.card_id ? ` · ${item.card_id}` : ''}
                      </div>
                      <div style={{ fontSize: '10px', color: 'var(--text-dim)', marginTop: '2px' }}>
                        {item.amount != null ? `${fmtMoney(item.amount)} · ` : ''}
                        {item.channel ? `${item.channel} · ` : ''}
                        {item.ts || ''}
                      </div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <span className="source-tag source-graph" style={{ fontSize: '9px' }}>
                        {matchTag}
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </>
      )}
    </aside>
  );
}
