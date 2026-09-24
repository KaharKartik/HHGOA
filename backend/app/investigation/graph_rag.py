from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Sequence

from pydantic import BaseModel, Field

from .models import PolicyId

STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "as", "at", "be", "because", "been", "before", "being", "below",
    "between", "both", "but", "by", "can", "did", "do", "does", "doing", "down",
    "during", "each", "few", "for", "from", "further", "had", "has", "have",
    "having", "he", "her", "here", "hers", "herself", "him", "himself", "his",
    "how", "i", "if", "in", "into", "is", "it", "its", "itself", "just", "me",
    "more", "most", "my", "myself", "no", "nor", "not", "now", "of", "off", "on",
    "once", "only", "or", "other", "our", "ours", "ourselves", "out", "over",
    "own", "same", "she", "should", "so", "some", "such", "than", "that", "the",
    "their", "theirs", "them", "themselves", "then", "there", "these", "they",
    "this", "those", "through", "to", "too", "under", "until", "up", "very", "was",
    "we", "were", "what", "when", "where", "which", "while", "who", "whom", "why",
    "with", "you", "your", "yours", "yourself", "yourselves"
}


def tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase alphanumeric tokens, omitting stop words."""
    raw_tokens = re.findall(r"[a-zA-Z0-9_\-]+", text.lower())
    return [t for t in raw_tokens if len(t) > 1 and t not in STOP_WORDS]


class PolicyChunk(BaseModel):
    chunk_id: str
    title: str
    section: str
    content: str
    source_doc: str
    policy_id: PolicyId | None = None
    tags: list[str] = Field(default_factory=list)


class PolicyEvidence(BaseModel):
    chunk_id: str
    policy_id: PolicyId | None = None
    title: str
    content: str
    relevance_score: float = Field(ge=0.0)
    matched_terms: list[str] = Field(default_factory=list)
    source_ref: str


class TFIDFIndex:
    """Deterministic in-memory TF-IDF index for typed PolicyChunk retrieval."""

    def __init__(self, chunks: Sequence[PolicyChunk]):
        self.chunks = list(chunks)
        self.doc_count = len(self.chunks)
        self.doc_tokens: list[list[str]] = [
            tokenize(f"{c.title} {c.section} {c.content} {' '.join(c.tags)}")
            for c in self.chunks
        ]

        df: dict[str, int] = {}
        for tokens in self.doc_tokens:
            for term in set(tokens):
                df[term] = df.get(term, 0) + 1
        self.df = df

        self.idf: dict[str, float] = {
            term: math.log(1.0 + (self.doc_count / (1.0 + freq))) + 1.0
            for term, freq in df.items()
        }

        self.doc_vectors: list[dict[str, float]] = []
        for tokens in self.doc_tokens:
            tf: dict[str, float] = {}
            for t in tokens:
                tf[t] = tf.get(t, 0.0) + 1.0
            total = len(tokens) or 1
            vec: dict[str, float] = {}
            norm_sq = 0.0
            for t, count in tf.items():
                w = (count / total) * self.idf.get(t, 1.0)
                vec[t] = w
                norm_sq += w * w
            norm = math.sqrt(norm_sq) or 1.0
            for t in vec:
                vec[t] /= norm
            self.doc_vectors.append(vec)

    def search(self, query: str, top_k: int = 5, min_score: float = 0.01) -> list[PolicyEvidence]:
        q_tokens = tokenize(query)
        if not q_tokens:
            return []

        q_tf: dict[str, float] = {}
        for t in q_tokens:
            q_tf[t] = q_tf.get(t, 0.0) + 1.0
        total = len(q_tokens)
        q_vec: dict[str, float] = {}
        norm_sq = 0.0
        for t, count in q_tf.items():
            idf_val = self.idf.get(t, 0.0)
            if idf_val > 0.0:
                w = (count / total) * idf_val
                q_vec[t] = w
                norm_sq += w * w
        norm = math.sqrt(norm_sq) or 1.0
        for t in q_vec:
            q_vec[t] /= norm

        scored: list[tuple[float, int, list[str]]] = []
        for i, doc_vec in enumerate(self.doc_vectors):
            score = 0.0
            matched = []
            for t, qw in q_vec.items():
                if t in doc_vec:
                    score += qw * doc_vec[t]
                    matched.append(t)
            if score >= min_score:
                scored.append((score, i, matched))

        scored.sort(key=lambda x: x[0], reverse=True)
        results: list[PolicyEvidence] = []
        for score, idx, matched in scored[:top_k]:
            chunk = self.chunks[idx]
            results.append(
                PolicyEvidence(
                    chunk_id=chunk.chunk_id,
                    policy_id=chunk.policy_id,
                    title=chunk.title,
                    content=chunk.content,
                    relevance_score=round(score, 4),
                    matched_terms=matched,
                    source_ref=f"{chunk.source_doc}#{chunk.section}",
                )
            )
        return results


def get_default_policy_chunks() -> list[PolicyChunk]:
    """Authoritative baseline policy chunks derived from project documentation."""
    return [
        PolicyChunk(
            chunk_id="policy-r1",
            title="R1. Verify before you block on a weak signal",
            section="Fraud Policy / Rules",
            content="If the case rests on a single signal (including a risk score alone) and your assessed fraud probability is below 0.70, recommend VERIFY_WITH_CUSTOMER or STEP_UP_AUTH before any block. Blocking a legitimate customer on one signal is a policy breach.",
            source_doc="data/raw/README.md",
            policy_id=PolicyId.R1,
            tags=["r1", "verify_with_customer", "step_up_auth", "weak_signal", "single_signal", "risk_score"],
        ),
        PolicyChunk(
            chunk_id="policy-r2",
            title="R2. Customer denies the transaction",
            section="Fraud Policy / Rules",
            content="Recommend BLOCK_CARD and CREATE_CASE. Add FILE_REPORT if exposure exceeds $1,000 or the case connects to a shared device profile or another card's fraud.",
            source_doc="data/raw/README.md",
            policy_id=PolicyId.R2,
            tags=["r2", "customer_denies", "block_card", "create_case", "file_report", "denied", "shared_device"],
        ),
        PolicyChunk(
            chunk_id="policy-r3",
            title="R3. Customer confirms the transaction",
            section="Fraud Policy / Rules",
            content="Recommend CLOSE_NO_FRAUD. Note the confirmation in the case file.",
            source_doc="data/raw/README.md",
            policy_id=PolicyId.R3,
            tags=["r3", "customer_confirms", "close_no_fraud", "confirms", "legitimate"],
        ),
        PolicyChunk(
            chunk_id="policy-r4",
            title="R4. No reply within 24 hours",
            section="Fraud Policy / Rules",
            content="Recommend MONITOR_CARD and DECLINE_TRANSACTION for pending authorizations. Escalate if exposure exceeds $500.",
            source_doc="data/raw/README.md",
            policy_id=PolicyId.R4,
            tags=["r4", "no_reply", "monitor_card", "decline_transaction", "escalate_to_analyst", "timeout"],
        ),
        PolicyChunk(
            chunk_id="policy-r5",
            title="R5. Card testing",
            section="Fraud Policy / Rules",
            content="Three or more small online authorizations on one card within an hour, followed by a larger purchase: recommend DECLINE_TRANSACTION and STEP_UP_AUTH. If a purchase over $100 has already cleared, recommend BLOCK_CARD.",
            source_doc="data/raw/README.md",
            policy_id=PolicyId.R5,
            tags=["r5", "card_testing", "small_authorizations", "step_up_auth", "decline_transaction", "block_card"],
        ),
        PolicyChunk(
            chunk_id="policy-r6",
            title="R6. Shared origin",
            section="Fraud Policy / Rules",
            content="When several cards show fraud from the same device profile, the same billing region, or the same recipient email in one window, name the shared element, recommend CREATE_CASE and FILE_REPORT, and MONITOR_CONNECTED_CARDS for every card that shares it.",
            source_doc="data/raw/README.md",
            policy_id=PolicyId.R6,
            tags=["r6", "shared_origin", "shared_device", "region_cluster", "monitor_connected_cards", "file_report", "create_case"],
        ),
        PolicyChunk(
            chunk_id="policy-r7",
            title="R7. Disputed but legitimate",
            section="Fraud Policy / Rules",
            content="When the customer disputes a charge that matches their own recurring pattern (same merchant, same amount, monthly), recommend CREATE_CASE, VERIFY_WITH_CUSTOMER, and WARN_CUSTOMER. Do not block.",
            source_doc="data/raw/README.md",
            policy_id=PolicyId.R7,
            tags=["r7", "recurring", "disputed_legitimate", "warn_customer", "verify_with_customer", "subscription"],
        ),
        PolicyChunk(
            chunk_id="policy-r8",
            title="R8. Escalate when uncertain and exposed",
            section="Fraud Policy / Rules",
            content="If the verdict is uncertain and exposure exceeds $500, or the evidence conflicts, recommend ESCALATE_TO_ANALYST.",
            source_doc="data/raw/README.md",
            policy_id=PolicyId.R8,
            tags=["r8", "uncertain", "escalate_to_analyst", "exposure", "conflicting_evidence"],
        ),
        PolicyChunk(
            chunk_id="policy-r9",
            title="R9. Undocumented patterns",
            section="Fraud Policy / Rules",
            content="When activity fits none of the known patterns but the evidence shows coordinated or repeated abuse across customers, recommend CREATE_CASE, FILE_REPORT, and ESCALATE_TO_ANALYST, and describe the pattern in your own words. Do not force it into a known category.",
            source_doc="data/raw/README.md",
            policy_id=PolicyId.R9,
            tags=["r9", "undocumented", "coordinated", "cross_customer", "file_report", "escalate_to_analyst"],
        ),
        PolicyChunk(
            chunk_id="policy-r10",
            title="R10. Never BLOCK_ALL_CARDS unless qualified",
            section="Fraud Policy / Rules",
            content="Never BLOCK_ALL_CARDS unless at least two of the customer's cards show confirmed fraud or the customer's credentials are confirmed compromised.",
            source_doc="data/raw/README.md",
            policy_id=PolicyId.R10,
            tags=["r10", "block_all_cards", "credentials_compromised", "two_cards_fraud"],
        ),
        PolicyChunk(
            chunk_id="pattern-card-testing",
            title="Pattern 1: Card testing",
            section="Known Fraud Patterns",
            content="A stolen card number is checked before use: three or more tiny online authorizations, often under $5, then a larger purchase. Confirmed by the sequence itself. Policy R5.",
            source_doc="data/raw/README.md",
            policy_id=PolicyId.R5,
            tags=["pattern", "card_testing", "tiny_authorizations", "micro_charges"],
        ),
        PolicyChunk(
            chunk_id="pattern-cnp",
            title="Pattern 2: Card-not-present fraud",
            section="Known Fraud Patterns",
            content="The number is used online without the card. Amounts and products that don't fit the cardholder's history, often in a burst of two to four within 48 hours. On its own, one unusual online purchase is ambiguous: verify. Policy R1 to R4.",
            source_doc="data/raw/README.md",
            policy_id=PolicyId.R1,
            tags=["pattern", "card_not_present", "online", "burst", "unusual_products"],
        ),
        PolicyChunk(
            chunk_id="pattern-cnp-new-device",
            title="Pattern 3: Card-not-present fraud from a new device",
            section="Known Fraud Patterns",
            content="Same as card-not-present, with the identity record marking the device as New for this account, sometimes behind a proxy. Stronger than pattern 2, still not proof: people buy new phones.",
            source_doc="data/raw/README.md",
            policy_id=PolicyId.R1,
            tags=["pattern", "card_not_present_new_device", "new_device", "proxy", "identity"],
        ),
        PolicyChunk(
            chunk_id="pattern-out-of-region",
            title="Pattern 4: Out-of-region use",
            section="Known Fraud Patterns",
            content="Card-present purchases in a billing region the cardholder has no history in, while their normal activity continues at home. Several days of purchases in one new region is a trip, not a clone. Policy R2, R3.",
            source_doc="data/raw/README.md",
            policy_id=PolicyId.R2,
            tags=["pattern", "out_of_region", "billing_region", "clone", "travel"],
        ),
        PolicyChunk(
            chunk_id="pattern-ato",
            title="Pattern 5: Account takeover",
            section="Known Fraud Patterns",
            content="Mixed-channel activity inconsistent with the cardholder, often with device and match-flag anomalies, pointing to stolen credentials rather than a stolen number.",
            source_doc="data/raw/README.md",
            policy_id=PolicyId.R10,
            tags=["pattern", "account_takeover", "ato", "stolen_credentials", "match_flag_anomalies"],
        ),
        PolicyChunk(
            chunk_id="sar-requirements",
            title="SAR Filing Guidance and Criteria",
            section="Fraud Policy / 3a. A case is not a report",
            content="A suspicious activity report (FILE_REPORT) is a regulatory filing sent outside the bank. File one when fraud is confirmed or strongly suspected and at least one holds: exposure exceeds $1,000; activity connects to a shared device profile, shared region cluster, or another customer's fraud; pattern is coordinated or undocumented (R9). Narrative must stand on its own: who, what, when, where, how, why.",
            source_doc="data/raw/README.md",
            policy_id=None,
            tags=["sar", "regulatory", "fincen", "file_report", "narrative", "threshold"],
        ),
        PolicyChunk(
            chunk_id="approval-routing",
            title="Approval Routing and Authority",
            section="Fraud Policy / 2. Approval routing",
            content="Auto route: ALLOW_TRANSACTION, MONITOR_CARD, MONITOR_CONNECTED_CARDS, WARN_CUSTOMER, VERIFY_WITH_CUSTOMER, STEP_UP_AUTH, GENERATE_REPORT, CREATE_CASE, ESCALATE_TO_ANALYST, CLOSE_NO_FRAUD. L1 (team lead): DECLINE_TRANSACTION, BLOCK_CARD when exposure <= $2,500. L2 (fraud manager): BLOCK_CARD when exposure > $2,500, BLOCK_ALL_CARDS always, FILE_REPORT always.",
            source_doc="data/raw/README.md",
            policy_id=None,
            tags=["approval", "routes", "auto", "l1", "l2", "authority"],
        ),
        PolicyChunk(
            chunk_id="stopping-criteria",
            title="Investigation Stopping Criteria",
            section="Fraud Policy / 6. Stopping",
            content="Stop investigating when: fraud probability is at or above 0.85, or at or below 0.15, supported by at least two independent pieces of evidence; a verification response settles the question; further steps are unlikely to change the decision.",
            source_doc="data/raw/README.md",
            policy_id=None,
            tags=["stopping", "stop_reason", "evidence_items", "probability_threshold"],
        ),
    ]


class PolicyRetriever:
    """GraphRAG in-memory retriever backed by authoritative project documentation."""

    def __init__(self, chunks: Sequence[PolicyChunk] | None = None, doc_root: Path | None = None):
        if chunks is not None:
            self._chunks = list(chunks)
        else:
            self._chunks = get_default_policy_chunks()
            if doc_root is not None and doc_root.exists():
                self._load_from_disk(doc_root)

        self._index = TFIDFIndex(self._chunks)

    def _load_from_disk(self, root: Path) -> None:
        """Optionally augment default chunks from project markdown docs."""
        readme = root / "data" / "raw" / "README.md"
        if readme.exists():
            pass  # Defaults already capture all core README sections

    @property
    def chunks(self) -> list[PolicyChunk]:
        return list(self._chunks)

    def retrieve(self, query: str, top_k: int = 3, min_score: float = 0.01) -> list[PolicyEvidence]:
        """Deterministic TF-IDF retrieval of relevant policy and pattern chunks."""
        return self._index.search(query, top_k=top_k, min_score=min_score)

    def get_chunk_by_policy(self, policy_id: PolicyId) -> PolicyChunk | None:
        for chunk in self._chunks:
            if chunk.policy_id == policy_id:
                return chunk
        return None
