from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.investigation.graph_service import (
    GraphEvidenceService,
    MockGraphEvidenceService,
    TigerGraphEvidenceService,
    TigerGraphMCPEvidenceService,
)


def test_mock_graph_service_set_and_get():
    service = MockGraphEvidenceService()
    service.set_customer_history("C100", [{"TransactionID": "T1", "amount": 50.0}])
    service.set_transaction_context("T1", {"Devices": ["D1"], "Emails": ["test.com"]})
    service.set_device_transactions("D1", [{"TransactionID": "T1", "card_id": "C100-K1"}])
    service.set_card_prior_cases("C100-K1", [{"case_id": "CC-99"}])
    service.set_transaction_sequence("T1", [{"transaction_id": "T2", "amount": 2.5}])

    assert len(service.get_customer_history("C100", "2016-01-01", "2016-12-31")) == 1
    assert service.get_transaction_context("T1")["Devices"] == ["D1"]
    assert len(service.get_device_neighbors("D1")) == 1
    assert len(service.get_card_prior_cases("C100-K1")) == 1
    assert len(service.get_transaction_sequence("T1")) == 1


def test_mock_graph_service_limits():
    service = MockGraphEvidenceService()
    service.set_customer_history("C1", [{"TransactionID": str(i)} for i in range(20)])
    res = service.get_customer_history("C1", "2016-01-01", "2016-12-31", limit=5)
    assert len(res) == 5


def test_tigergraph_restpp_adapter_service():
    mock_adapter = MagicMock()
    mock_res = MagicMock()
    mock_res.data = [{"TransactionID": "T1", "amount": 100.0}]
    mock_adapter.get_customer_transactions.return_value = mock_res
    mock_adapter.get_transaction_context.return_value = MagicMock(data={"Devices": ["D1"]})

    service = TigerGraphEvidenceService(mock_adapter)
    history = service.get_customer_history("C1", "2016-01-01", "2016-12-31")
    assert len(history) == 1
    assert history[0]["TransactionID"] == "T1"

    ctx = service.get_transaction_context("T1")
    assert ctx["Devices"] == ["D1"]


def test_tigergraph_mcp_service_without_client_raises():
    service = TigerGraphMCPEvidenceService()
    assert not service.is_connected
    with pytest.raises(NotImplementedError) as exc_info:
        service.get_customer_history("C1", "2016-01-01", "2016-12-31")
    assert "MCP client is not configured" in str(exc_info.value)


def test_tigergraph_mcp_service_with_injected_client():
    class FakeMCPClient:
        def call_tool(self, tool_name: str, arguments: dict):
            assert tool_name == "tigergraph__run_installed_query"
            return {"results": [{"TransactionID": "T123", "amount": 42.0}]}

    client = FakeMCPClient()
    service = TigerGraphMCPEvidenceService(mcp_client=client)
    assert service.is_connected

    res = service.get_customer_history("C1", "2016-01-01", "2016-12-31")
    assert len(res) == 1
    assert res[0]["TransactionID"] == "T123"
