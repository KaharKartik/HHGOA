from __future__ import annotations

import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.investigation.graph_rag import (
    PolicyChunk,
    PolicyEvidence,
    PolicyRetriever,
    TFIDFIndex,
    tokenize,
)
from app.investigation.models import PolicyId


def test_tokenize():
    tokens = tokenize("Customer disputes a charge matching recurring monthly subscription!")
    assert "customer" in tokens
    assert "disputes" in tokens
    assert "charge" in tokens
    assert "recurring" in tokens
    assert "subscription" in tokens
    # Stop words like 'a' are removed
    assert "a" not in tokens


def test_policy_chunk_and_evidence_models():
    chunk = PolicyChunk(
        chunk_id="chk-1",
        title="Test Policy",
        section="Test Section",
        content="Test content for verification.",
        source_doc="data/raw/README.md",
        policy_id=PolicyId.R1,
        tags=["test", "verify"],
    )
    assert chunk.policy_id is PolicyId.R1
    assert chunk.tags == ["test", "verify"]

    evidence = PolicyEvidence(
        chunk_id="chk-1",
        policy_id=PolicyId.R1,
        title="Test Policy",
        content="Test content",
        relevance_score=0.85,
        matched_terms=["verify"],
        source_ref="data/raw/README.md#Test Section",
    )
    assert evidence.relevance_score == 0.85
    assert evidence.matched_terms == ["verify"]


def test_tfidf_retrieval_card_testing():
    retriever = PolicyRetriever()
    results = retriever.retrieve("card testing rapid small authorizations followed by large purchase", top_k=3)
    assert len(results) > 0
    top = results[0]
    assert top.policy_id == PolicyId.R5
    assert "testing" in top.matched_terms or "card" in top.matched_terms


def test_tfidf_retrieval_recurring_subscription():
    retriever = PolicyRetriever()
    results = retriever.retrieve("disputed recurring pattern same merchant monthly charge", top_k=3)
    assert len(results) > 0
    top = results[0]
    assert top.policy_id == PolicyId.R7


def test_tfidf_retrieval_sar_guidance():
    retriever = PolicyRetriever()
    results = retriever.retrieve("suspicious activity report filing threshold fincen narrative", top_k=3)
    assert len(results) > 0
    # Top result should reference SAR requirements or R2/R6/R9
    assert any("sar" in r.chunk_id.lower() or "report" in r.title.lower() for r in results)


def test_tfidf_deterministic():
    retriever = PolicyRetriever()
    query = "weak signal verify before block on single risk score"
    res1 = retriever.retrieve(query, top_k=3)
    res2 = retriever.retrieve(query, top_k=3)
    assert [r.chunk_id for r in res1] == [r.chunk_id for r in res2]
    assert [r.relevance_score for r in res1] == [r.relevance_score for r in res2]


def test_policy_retriever_get_by_id():
    retriever = PolicyRetriever()
    r1 = retriever.get_chunk_by_policy(PolicyId.R1)
    assert r1 is not None
    assert "Verify before you block" in r1.title
    assert r1.policy_id == PolicyId.R1

    r10 = retriever.get_chunk_by_policy(PolicyId.R10)
    assert r10 is not None
    assert "BLOCK_ALL_CARDS" in r10.content
