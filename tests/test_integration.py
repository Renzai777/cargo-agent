"""
End-to-end integration test — runs the full LangGraph pipeline
against the temp_spike scenario without mocking Claude.
Set ANTHROPIC_API_KEY in environment before running.
Skip with: pytest -m "not integration"
"""
import pytest
from src.graph.cargo_graph import build_graph
from src.simulator.scenarios import scenario_temp_spike
from src.graph.state import CargoState

pytestmark = pytest.mark.integration


def test_temp_spike_scenario_reaches_high_severity():
    graph = build_graph(db_path=":memory:")
    shipment_id = "SHP-INTEGRATION-001"
    config = {"configurable": {"thread_id": shipment_id}}

    initial_state: dict = {
        "shipment_id": shipment_id,
        "cargo_type": "vaccine",
        "cargo_description": "COVID-19 mRNA Vaccine — 500 doses",
        "origin_city": "New York",
        "destination_city": "Nairobi",
        "expected_arrival": None,
        "telemetry_window": [],
        "latest_reading": None,
        "anomalies": [],
        "spoilage_probability": 0.0,
        "delay_risk": 0.0,
        "severity": "LOW",
        "recommended_actions": [],
        "orchestrator_reasoning": "",
        "route_recommendation": None,
        "notifications_sent": [],
        "cold_storage_booked": False,
        "cold_storage_facility": None,
        "insurance_claim_id": None,
        "audit_log": [],
        "gdp_compliant": True,
        "awaiting_human_approval": False,
        "human_decision": None,
        "human_notes": None,
    }
    graph.update_state(config, initial_state)

    readings = scenario_temp_spike(shipment_id=shipment_id)
    final_state = None
    for reading in readings:
        final_state = graph.invoke(
            {"latest_reading": reading, "telemetry_window": [reading]},
            config=config
        )

    assert final_state is not None
    assert final_state["severity"] in ("HIGH", "CRITICAL")
    assert len(final_state["audit_log"]) > 0
