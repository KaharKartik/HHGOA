"""Agent package entry point re-exporting investigation models and agent foundation."""
import sys
from pathlib import Path

# Ensure backend package is in python path
_BACKEND_DIR = str(Path(__file__).resolve().parents[2] / "backend")
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from app.investigation import (
    ClosedCase,
    ClosedCaseRepository,
    GraphEvidenceService,
    InMemoryClosedCaseRepository,
    InvestigationAgent,
    InvestigationCaseWriter,
    InvestigationCaseWriterStub,
    InvestigationResult,
    InvestigationState,
    MCPToolClient,
    MockGraphEvidenceService,
    PolicyChunk,
    PolicyEngine,
    PolicyEvidence,
    PolicyRetriever,
    TFIDFIndex,
    TigerGraphEvidenceService,
    TigerGraphMCPEvidenceService,
)

__all__ = [
    "InvestigationAgent",
    "InvestigationState",
    "GraphEvidenceService",
    "MockGraphEvidenceService",
    "TigerGraphEvidenceService",
    "TigerGraphMCPEvidenceService",
    "MCPToolClient",
    "PolicyChunk",
    "PolicyEvidence",
    "PolicyRetriever",
    "TFIDFIndex",
    "ClosedCase",
    "ClosedCaseRepository",
    "InMemoryClosedCaseRepository",
    "InvestigationCaseWriter",
    "InvestigationCaseWriterStub",
    "InvestigationResult",
    "PolicyEngine",
]
