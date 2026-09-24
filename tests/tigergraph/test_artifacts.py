import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))

from app.integrations.tigergraph import TigerGraphAdapter, TigerGraphError


def test_schema_vertices_and_edges_exist():
    text=(ROOT/'tigergraph/schema/fraud_investigation_schema.gsql').read_text()
    for name in ['Customer','Card','Transaction','DeviceProfile','EmailDomain','BillingRegion','ClosedCase','InvestigationCase','OWNS','FROM_DEVICE','SIMILAR_TO']:
        assert name in text


def test_required_queries_exist():
    text=(ROOT/'tigergraph/queries/investigation_queries.gsql').read_text()

    for name in [
        'device_neighbors',
        'shared_device_transactions',
        'prior_case_neighbors',
        'card_connected_cases',
        'case_context',
        'transaction_sequence',
        'region_transactions',
        'email_transactions',
        'customer_transactions',
        'transaction_context',
        'connected_cards_from_case'
    ]:
        assert f'QUERY {name}' in text

    assert text.count('CREATE QUERY') == 11
    assert 'USE GRAPH HHGOA_FRAUD' in text
    assert 'FOR GRAPH FraudInvestigationGraph' not in text
    assert 'MADE' not in text


def test_adapter_queries_are_defined_and_use_actual_graph():
    import inspect
    import re

    from app.integrations.tigergraph import TigerGraphAdapter

    queries=set(
        re.findall(
            r'CREATE QUERY\s+(\w+)',
            (ROOT/'tigergraph/queries/investigation_queries.gsql').read_text()
        )
    )

    methods=[
        name
        for name,fn in inspect.getmembers(
            TigerGraphAdapter,
            inspect.isfunction
        )
        if name.startswith('get_') and name not in {'get_schema'}
    ]

    mapped=set()

    for name in methods:
        source=inspect.getsource(getattr(TigerGraphAdapter,name))
        matches=re.findall(
            r"_query\(\s*['\"]([^'\"]+)['\"]",
            source
        )
        mapped.update(matches)

    assert mapped <= queries
    assert 'MADE' not in inspect.getsource(TigerGraphAdapter)
    assert TigerGraphAdapter('http://localhost','HHGOA_FRAUD').graph_name == 'HHGOA_FRAUD'


def test_loading_uses_all_required_sources():
    text=(ROOT/'tigergraph/loading/load_fraud_data.gsql').read_text()
    for name in ['transactions','identity_profiles','closed_cases','case_pack']:
        assert name in text


def test_adapter_has_predictable_missing_connection_error():
    adapter=TigerGraphAdapter(
        'http://127.0.0.1:1',
        'HHGOA_FRAUD',
        timeout_s=.01
    )

    try:
        adapter.get_device_neighbors('DP-test')
    except TigerGraphError as error:
        assert 'device_neighbors' in str(error)
    else:
        raise AssertionError('connection unexpectedly succeeded')