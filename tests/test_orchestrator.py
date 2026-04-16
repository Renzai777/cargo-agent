import pytest
from unittest.mock import patch, MagicMock
from src.agents.orchestrator import orchestrator_agent
from src.graph.state import AnomalyRecord


@pytest.fixture
def critical_state(base_state):
    anomaly = AnomalyRecord(
        shipment_id="SHP-TEST-001",
        anomaly_type="temp_excursion",
        severity="CRITICAL",
        z_score=5.1,
        description="Refrigeration failure — temp 18°C",
        raw_value=18.0,
        threshold_value=8.0,
    )
    return {**base_state, "anomalies": [anomaly], "spoilage_probability": 0.85, "severity": "CRITICAL"}


def test_orchestrator_returns_actions(critical_state):
    mock_resp = MagicMock()
    mock_resp.stop_reason = "end_turn"
    mock_resp.content = [MagicMock(type="text", text="Triggering REROUTE and NOTIFY_HOSPITALS due to CRITICAL spoilage risk.")]

    with patch("src.agents.orchestrator.client.messages.create", return_value=mock_resp):
        result = orchestrator_agent(critical_state)

    assert "recommended_actions" in result
    assert isinstance(result["recommended_actions"], list)


def test_orchestrator_always_includes_compliance(critical_state):
    mock_resp = MagicMock()
    mock_resp.stop_reason = "end_turn"
    mock_resp.content = [MagicMock(type="text", text="REROUTE NOTIFY_HOSPITALS COLD_STORAGE FILE_INSURANCE")]

    with patch("src.agents.orchestrator.client.messages.create", return_value=mock_resp):
        result = orchestrator_agent(critical_state)

    assert len(result["audit_log"]) >= 1
    assert result["audit_log"][0].agent_name == "orchestrator_agent"
