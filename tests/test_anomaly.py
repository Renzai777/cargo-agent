import pytest
from unittest.mock import patch, MagicMock
from src.agents.anomaly_detector import anomaly_agent
from src.graph.state import AnomalyRecord


def test_no_anomalies_with_clean_window(base_state):
    """When all readings are normal, no anomalies should be added."""
    result = anomaly_agent(base_state)
    assert result.get("anomalies", []) == []


def test_high_zscore_triggers_llm_call(base_state, spike_reading):
    """Z-score > 3 should trigger LLM analysis."""
    state = {**base_state, "latest_reading": spike_reading}
    from src.simulator.telemetry import TelemetrySimulator
    sim = TelemetrySimulator("vaccine", "SHP-TEST-001")
    state["telemetry_window"] = sim.generate_batch(10)

    mock_response = MagicMock()
    mock_response.content = [MagicMock(
        text='{"severity": "CRITICAL", "description": "Severe temperature excursion detected — refrigeration likely failed.", "anomaly_type": "temp_excursion"}'
    )]

    with patch("src.agents.anomaly_detector.client.messages.create", return_value=mock_response):
        result = anomaly_agent(state)

    assert len(result["anomalies"]) > 0
    assert result["anomalies"][0].severity == "CRITICAL"


def test_low_zscore_no_llm_call(base_state):
    """Z-score < 3 should not trigger LLM — no new anomalies added."""
    from src.simulator.telemetry import TelemetrySimulator
    sim = TelemetrySimulator("vaccine", "SHP-TEST-001")
    state = {**base_state, "telemetry_window": sim.generate_batch(10)}

    with patch("src.agents.anomaly_detector.client.messages.create") as mock_llm:
        result = anomaly_agent(state)
        mock_llm.assert_not_called()

    assert result.get("anomalies", []) == []
