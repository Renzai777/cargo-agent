import pytest
from src.graph.cargo_graph import build_graph


def test_graph_compiles():
    graph = build_graph()
    assert graph is not None


def test_graph_has_expected_nodes():
    graph = build_graph()
    node_names = set(graph.nodes.keys())
    expected = {
        "monitor_agent", "anomaly_agent", "risk_agent",
        "decision_orchestrator", "route_optimizer",
        "notification_agent", "inventory_agent",
        "cold_storage_agent", "insurance_agent", "compliance_agent"
    }
    assert expected.issubset(node_names)
