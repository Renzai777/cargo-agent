import pytest
from src.agents.monitor import monitor_agent


def test_no_breach_returns_empty_anomalies(base_state):
    result = monitor_agent(base_state)
    assert result["anomalies"] == []
    assert len(result["audit_log"]) == 1
    assert result["audit_log"][0].action_type == "THRESHOLD_CHECK"


def test_temp_breach_detected(base_state, spike_reading):
    state = {**base_state, "latest_reading": spike_reading}
    result = monitor_agent(state)
    assert any("temp" in a.anomaly_type for a in result["anomalies"])


def test_customs_hold_detected(base_state, sample_reading):
    held = sample_reading.model_copy(update={"customs_status": "held"})
    state = {**base_state, "latest_reading": held}
    result = monitor_agent(state)
    assert any("customs" in a.anomaly_type for a in result["anomalies"])


def test_shock_breach_detected(base_state, sample_reading):
    shock = sample_reading.model_copy(update={"shock_g": 4.5})
    state = {**base_state, "latest_reading": shock}
    result = monitor_agent(state)
    assert any("shock" in a.anomaly_type for a in result["anomalies"])
