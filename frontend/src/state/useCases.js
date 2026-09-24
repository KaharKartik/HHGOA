import { useState, useEffect, useMemo, useCallback } from 'react';
import {
  fetchCases,
  fetchCaseDetails,
  searchTransactions,
  fetchTransactionDetails,
  generateFallbackCases,
} from '../api/casesApi';

export function useCases() {
  const [allCases, setAllCases] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [activeCaseData, setActiveCaseData] = useState(null);
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);
  const [detailError, setDetailError] = useState(null);
  const [isOnline, setIsOnline] = useState(false);
  const [statusText, setStatusText] = useState('Connecting…');
  const [searchQuery, setSearchQuery] = useState('');
  const [currentFilter, setCurrentFilter] = useState('all');

  // Live Investigation / Global Search Mode
  const [activeMode, setActiveMode] = useState('queue'); // 'queue' | 'live'
  const [globalQuery, setGlobalQuery] = useState('');
  const [searchType, setSearchType] = useState('all'); // 'all' | 'transaction' | 'customer' | 'card' | 'device'
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState([]);
  const [searchLatency, setSearchLatency] = useState(null);
  const [searchError, setSearchError] = useState(null);

  // Selected Live Transaction State
  const [selectedTxnId, setSelectedTxnId] = useState(null);
  const [activeTxnData, setActiveTxnData] = useState(null);
  const [isLoadingTxn, setIsLoadingTxn] = useState(false);
  const [txnError, setTxnError] = useState(null);

  const loadCases = useCallback(async () => {
    try {
      const data = await fetchCases();
      setAllCases(data.cases || []);
      setIsOnline(true);
      setStatusText('TigerGraph Savanna Live');
    } catch (e) {
      console.warn("API offline, utilizing benchmark fallback:", e);
      setIsOnline(false);
      setStatusText('API Offline · Fallback Mode');
      setAllCases(generateFallbackCases());
    }
  }, []);

  useEffect(() => {
    loadCases();
  }, [loadCases]);

  const selectCase = useCallback(async (caseId) => {
    setActiveId(caseId);
    setActiveCaseData(null);
    setDetailError(null);
    setIsLoadingDetails(true);
    // Reset selected live transaction when selecting a benchmark case
    setSelectedTxnId(null);
    setActiveTxnData(null);

    try {
      const data = await fetchCaseDetails(caseId);
      setActiveCaseData(data);
      setAllCases(prev => prev.map(c => {
        if (c.case_id === caseId) {
          return {
            ...c,
            verdict: data.verdict,
            flagged_txn_id: data.flagged_transaction_id || c.flagged_txn_id
          };
        }
        return c;
      }));
    } catch (e) {
      setDetailError(e.message);
    } finally {
      setIsLoadingDetails(false);
    }
  }, []);

  const executeSearch = useCallback(async (query, type) => {
    const q = (query !== undefined ? query : globalQuery).trim();
    const t = type !== undefined ? type : searchType;
    if (!q) {
      setSearchResults([]);
      setSearchLatency(null);
      setSearchError(null);
      return;
    }
    setIsSearching(true);
    setSearchError(null);
    try {
      const data = await searchTransactions(q, t);
      setSearchResults(data.results || []);
      setSearchLatency(data.latency_ms);
    } catch (e) {
      setSearchError(e.message);
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  }, [globalQuery, searchType]);

  const selectTransaction = useCallback(async (txnId) => {
    setSelectedTxnId(txnId);
    setActiveTxnData(null);
    setTxnError(null);
    setIsLoadingTxn(true);
    // Reset benchmark case view when viewing a live transaction
    setActiveId(null);
    setActiveCaseData(null);

    try {
      const data = await fetchTransactionDetails(txnId);
      setActiveTxnData(data);
    } catch (e) {
      setTxnError(e.message);
    } finally {
      setIsLoadingTxn(false);
    }
  }, []);

  const counts = useMemo(() => {
    return {
      all: allCases.length,
      fraud: allCases.filter(c => (c.verdict || '').toLowerCase() === 'fraud').length,
      legit: allCases.filter(c => (c.verdict || '').toLowerCase() === 'legitimate').length,
      uncertain: allCases.filter(c => c.verdict && (c.verdict || '').toLowerCase() !== 'fraud' && (c.verdict || '').toLowerCase() !== 'legitimate').length,
    };
  }, [allCases]);

  const filteredCases = useMemo(() => {
    const q = searchQuery.toLowerCase().trim();
    return allCases.filter(c => {
      const matchesQuery = (c.case_id || '').toLowerCase().includes(q) ||
                           (c.flagged_txn_id || c.flagged_transaction_id || '').toLowerCase().includes(q);
      if (!matchesQuery) return false;

      if (currentFilter === 'fraud') return (c.verdict || '').toLowerCase() === 'fraud';
      if (currentFilter === 'legit') return (c.verdict || '').toLowerCase() === 'legitimate';
      if (currentFilter === 'uncertain') return c.verdict && (c.verdict || '').toLowerCase() !== 'fraud' && (c.verdict || '').toLowerCase() !== 'legitimate';
      return true;
    });
  }, [allCases, searchQuery, currentFilter]);

  return {
    allCases,
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

    // Live search & transaction investigation
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
  };
}
