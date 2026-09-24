from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Protocol


class GraphEvidenceService(ABC):
    """Abstract service boundary for retrieving graph facts during fraud investigation.

    All graph queries used by the investigation agent must go through this interface,
    allowing clean substitution between deterministic mocks (for tests), REST++ query
    adapters, and the TigerGraph MCP client runtime boundary.
    """

    @abstractmethod
    def get_customer_history(
        self, customer_id: str, start_ts: str, end_ts: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Retrieve customer transaction history across a time window."""
        ...

    @abstractmethod
    def get_transaction_context(self, transaction_id: str, limit: int = 100) -> dict[str, Any]:
        """Retrieve 1-hop context of a transaction: device, email, region, next txns."""
        ...

    @abstractmethod
    def get_device_neighbors(
        self, device_profile_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Retrieve all transactions originating from a device profile."""
        ...

    @abstractmethod
    def get_shared_device_transactions(
        self, device_profile_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Retrieve transactions across all cards sharing a device profile."""
        ...

    @abstractmethod
    def get_card_prior_cases(self, card_id: str, limit: int = 100) -> list[dict[str, Any]]:
        """Retrieve closed cases previously associated with this card."""
        ...

    @abstractmethod
    def get_card_connected_cases(self, card_id: str, limit: int = 100) -> list[dict[str, Any]]:
        """Retrieve closed cases connected to this card via compromise rings."""
        ...

    @abstractmethod
    def get_transaction_sequence(
        self, transaction_id: str, limit: int = 20
    ) -> list[dict[str, Any]]:
        """Retrieve subsequent transaction sequence linked by NEXT edges."""
        ...

    @abstractmethod
    def get_region_transactions(
        self, region_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Retrieve transactions within a billing region."""
        ...

    @abstractmethod
    def get_email_transactions(
        self, email_domain: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Retrieve transactions associated with an email domain."""
        ...

    @abstractmethod
    def get_connected_cards_from_case(
        self, case_id: str, limit: int = 100
    ) -> dict[str, list[dict[str, Any]]]:
        """Retrieve cards directly on or connected to a closed case."""
        ...


class MockGraphEvidenceService(GraphEvidenceService):
    """Deterministic in-memory graph service for automated tests and offline verification."""

    def __init__(self, fixtures: dict[str, Any] | None = None):
        self._fixtures = fixtures or {}
        self._customer_history: dict[str, list[dict[str, Any]]] = self._fixtures.get(
            "customer_history", {}
        )
        self._tx_contexts: dict[str, dict[str, Any]] = self._fixtures.get("tx_contexts", {})
        self._device_txns: dict[str, list[dict[str, Any]]] = self._fixtures.get(
            "device_txns", {}
        )
        self._card_prior_cases: dict[str, list[dict[str, Any]]] = self._fixtures.get(
            "card_prior_cases", {}
        )
        self._card_connected_cases: dict[str, list[dict[str, Any]]] = self._fixtures.get(
            "card_connected_cases", {}
        )
        self._sequences: dict[str, list[dict[str, Any]]] = self._fixtures.get("sequences", {})
        self._region_txns: dict[str, list[dict[str, Any]]] = self._fixtures.get(
            "region_txns", {}
        )
        self._email_txns: dict[str, list[dict[str, Any]]] = self._fixtures.get("email_txns", {})
        self._case_connected_cards: dict[str, dict[str, list[dict[str, Any]]]] = (
            self._fixtures.get("case_connected_cards", {})
        )

    def set_customer_history(self, customer_id: str, transactions: list[dict[str, Any]]) -> None:
        self._customer_history[customer_id] = transactions

    def set_transaction_context(self, transaction_id: str, context: dict[str, Any]) -> None:
        self._tx_contexts[transaction_id] = context

    def set_device_transactions(
        self, device_profile_id: str, transactions: list[dict[str, Any]]
    ) -> None:
        self._device_txns[device_profile_id] = transactions

    def set_card_prior_cases(self, card_id: str, cases: list[dict[str, Any]]) -> None:
        self._card_prior_cases[card_id] = cases

    def set_transaction_sequence(
        self, transaction_id: str, sequence: list[dict[str, Any]]
    ) -> None:
        self._sequences[transaction_id] = sequence

    def get_customer_history(
        self, customer_id: str, start_ts: str, end_ts: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        history = self._customer_history.get(customer_id, [])
        return history[:limit]

    def get_transaction_context(self, transaction_id: str, limit: int = 100) -> dict[str, Any]:
        return self._tx_contexts.get(
            transaction_id,
            {"Devices": [], "Emails": [], "Regions": [], "NextTransactions": []},
        )

    def get_device_neighbors(
        self, device_profile_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        return self._device_txns.get(device_profile_id, [])[:limit]

    def get_shared_device_transactions(
        self, device_profile_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        return self._device_txns.get(device_profile_id, [])[:limit]

    def get_card_prior_cases(self, card_id: str, limit: int = 100) -> list[dict[str, Any]]:
        return self._card_prior_cases.get(card_id, [])[:limit]

    def get_card_connected_cases(self, card_id: str, limit: int = 100) -> list[dict[str, Any]]:
        return self._card_connected_cases.get(card_id, [])[:limit]

    def get_transaction_sequence(
        self, transaction_id: str, limit: int = 20
    ) -> list[dict[str, Any]]:
        return self._sequences.get(transaction_id, [])[:limit]

    def get_region_transactions(
        self, region_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        return self._region_txns.get(region_id, [])[:limit]

    def get_email_transactions(
        self, email_domain: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        return self._email_txns.get(email_domain, [])[:limit]

    def get_connected_cards_from_case(
        self, case_id: str, limit: int = 100
    ) -> dict[str, list[dict[str, Any]]]:
        return self._case_connected_cards.get(
            case_id, {"ConnectedCards": [], "CaseCards": []}
        )


class TigerGraphRESTPPEvidenceService(GraphEvidenceService):
    """Production REST++ query adapter invoking installed TigerGraph GSQL queries."""

    def __init__(self, adapter: Any):
        self._adapter = adapter

    def get_customer_history(
        self, customer_id: str, start_ts: str, end_ts: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        res = self._adapter.get_customer_transactions(
            customer_id=customer_id, start_ts=start_ts, end_ts=end_ts, limit=limit
        )
        return getattr(res, "data", []) or []

    def get_transaction_context(self, transaction_id: str, limit: int = 100) -> dict[str, Any]:
        res = self._adapter.get_transaction_context(transaction_id=transaction_id, limit=limit)
        return getattr(res, "data", {}) or {}

    def get_device_neighbors(
        self, device_profile_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        res = self._adapter.get_device_neighbors(device_profile_id=device_profile_id, limit=limit)
        return getattr(res, "data", []) or []

    def get_shared_device_transactions(
        self, device_profile_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        res = self._adapter.get_shared_device_transactions(
            device_profile_id=device_profile_id, limit=limit
        )
        return getattr(res, "data", []) or []

    def get_card_prior_cases(self, card_id: str, limit: int = 100) -> list[dict[str, Any]]:
        res = self._adapter.get_prior_cases(card_id=card_id, limit=limit)
        return getattr(res, "data", []) or []

    def get_card_connected_cases(self, card_id: str, limit: int = 100) -> list[dict[str, Any]]:
        res = self._adapter.get_card_connected_cases(card_id=card_id, limit=limit)
        return getattr(res, "data", []) or []

    def get_transaction_sequence(
        self, transaction_id: str, limit: int = 20
    ) -> list[dict[str, Any]]:
        res = self._adapter.get_transaction_sequence(transaction_id=transaction_id, limit=limit)
        return getattr(res, "data", []) or []

    def get_region_transactions(
        self, region_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        res = self._adapter.get_region_transactions(region_id=region_id, limit=limit)
        return getattr(res, "data", []) or []

    def get_email_transactions(
        self, email_domain: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        res = self._adapter.get_email_transactions(email_domain=email_domain, limit=limit)
        return getattr(res, "data", []) or []

    def get_connected_cards_from_case(
        self, case_id: str, limit: int = 100
    ) -> dict[str, list[dict[str, Any]]]:
        res = self._adapter.get_connected_cards_from_case(case_id=case_id, limit=limit)
        return getattr(res, "data", {}) or {"ConnectedCards": [], "CaseCards": []}


class MCPToolClient(Protocol):
    """Protocol for runtime MCP tool execution.

    Any MCP client (such as stdio, SSE, or agent runtime adapter) that exposes tool calling
    can implement this protocol to back TigerGraphMCPEvidenceService.
    """

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute tool on the MCP server and return parsed JSON result."""
        ...


class TigerGraphMCPEvidenceService(GraphEvidenceService):
    """Runtime adapter boundary for TigerGraph MCP tool execution.

    This class serves as the clean plug-in boundary between the investigation agent
    and the real TigerGraph MCP server. The Antigravity MCP connection is not hardcoded
    into application logic; instead, an instance of MCPToolClient is injected at runtime.
    """

    def __init__(self, mcp_client: MCPToolClient | None = None):
        self._mcp_client = mcp_client

    @property
    def is_connected(self) -> bool:
        return self._mcp_client is not None

    def _invoke(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if self._mcp_client is None:
            raise NotImplementedError(
                f"TigerGraph MCP client is not configured for '{tool_name}'. "
                "Inject a valid MCPToolClient implementation into TigerGraphMCPEvidenceService "
                "at runtime to connect with live TigerGraph MCP tools."
            )
        return self._mcp_client.call_tool(tool_name, arguments)

    def get_customer_history(
        self, customer_id: str, start_ts: str, end_ts: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        result = self._invoke(
            "tigergraph__run_installed_query",
            {
                "query_name": "customer_transactions",
                "params": {"customer": customer_id, "start_ts": start_ts, "end_ts": end_ts, "max_results": limit},
            },
        )
        return result.get("results", [])

    def get_transaction_context(self, transaction_id: str, limit: int = 100) -> dict[str, Any]:
        return self._invoke(
            "tigergraph__run_installed_query",
            {
                "query_name": "transaction_context",
                "params": {"transaction": transaction_id, "max_results": limit},
            },
        )

    def get_device_neighbors(
        self, device_profile_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        result = self._invoke(
            "tigergraph__run_installed_query",
            {
                "query_name": "device_neighbors",
                "params": {"device": device_profile_id, "max_results": limit},
            },
        )
        return result.get("results", [])

    def get_shared_device_transactions(
        self, device_profile_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        result = self._invoke(
            "tigergraph__run_installed_query",
            {
                "query_name": "shared_device_transactions",
                "params": {"device": device_profile_id, "max_results": limit},
            },
        )
        return result.get("results", [])

    def get_card_prior_cases(self, card_id: str, limit: int = 100) -> list[dict[str, Any]]:
        result = self._invoke(
            "tigergraph__run_installed_query",
            {
                "query_name": "prior_case_neighbors",
                "params": {"card": card_id, "max_results": limit},
            },
        )
        return result.get("results", [])

    def get_card_connected_cases(self, card_id: str, limit: int = 100) -> list[dict[str, Any]]:
        result = self._invoke(
            "tigergraph__run_installed_query",
            {
                "query_name": "card_connected_cases",
                "params": {"card": card_id, "max_results": limit},
            },
        )
        return result.get("results", [])

    def get_transaction_sequence(
        self, transaction_id: str, limit: int = 20
    ) -> list[dict[str, Any]]:
        result = self._invoke(
            "tigergraph__run_installed_query",
            {
                "query_name": "transaction_sequence",
                "params": {"transaction": transaction_id, "max_results": limit},
            },
        )
        return result.get("results", [])

    def get_region_transactions(
        self, region_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        result = self._invoke(
            "tigergraph__run_installed_query",
            {
                "query_name": "region_transactions",
                "params": {"region": region_id, "max_results": limit},
            },
        )
        return result.get("results", [])

    def get_email_transactions(
        self, email_domain: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        result = self._invoke(
            "tigergraph__run_installed_query",
            {
                "query_name": "email_transactions",
                "params": {"email": email_domain, "max_results": limit},
            },
        )
        return result.get("results", [])

    def get_connected_cards_from_case(
        self, case_id: str, limit: int = 100
    ) -> dict[str, list[dict[str, Any]]]:
        return self._invoke(
            "tigergraph__run_installed_query",
            {
                "query_name": "connected_cards_from_case",
                "params": {"closed_case": case_id, "max_results": limit},
            },
        )


# Alias for backward and forward compatibility
TigerGraphEvidenceService = TigerGraphRESTPPEvidenceService
