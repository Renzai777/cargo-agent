import pytest
from unittest.mock import patch, MagicMock
from src.agents.risk_assessor import risk_agent
from src.graph.state import AnomalyRecord
from datetime import datetime


@pytest.fixture
def state_with_anomaly(base_state):
    anomaly = AnomalyRecord(
        shipment_id="SHP-TEST-001",
        anomaly_type="temp_excursion",
        severity="HIGH",
        z_score=4.2,
        description="Temperature 16.5°C exceeds 8°C max",
        raw_value=16.5,
        threshold_value=8.0,
    )
    return {**base_state, "anomalies": [anomaly]}


def test_no_anomalies_returns_low_risk(base_state):
    result = risk_agent(base_state)
    assert result["severity"] == "LOW"
    assert result["spoilage_probability"] == 0.0


def test_anomaly_calls_claude_and_returns_risk(state_with_anomaly):
    mock_resp = MagicMock()
    mock_resp.stop_reason = "end_turn"
    mock_resp.content = [MagicMock(
        type="text",
        text='{"spoilage_probability": 0.72, "delay_risk": 0.45, "severity": "CRITICAL", "reasoning": "High temp excursion with 8h remaining route time — vaccine viability severely threatened."}'
    )]

    with patch("src.agents.risk_assessor.client.messages.create", return_value=mock_resp):
        result = risk_agent(state_with_anomaly)

    assert result["spoilage_probability"] == 0.72
    assert result["severity"] == "CRITICAL"


def test_risk_audit_entry_written(state_with_anomaly):
    mock_resp = MagicMock()
    mock_resp.stop_reason = "end_turn"
    mock_resp.content = [MagicMock(
        type="text",
        text='{"spoilage_probability": 0.5, "delay_risk": 0.3, "severity": "HIGH", "reasoning": "Moderate risk."}'
    )]

    with patch("src.agents.risk_assessor.client.messages.create", return_value=mock_resp):
        result = risk_agent(state_with_anomaly)

    assert len(result["audit_log"]) >= 1
    assert result["audit_log"][0].agent_name == "risk_agent"
