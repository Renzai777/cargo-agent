import pytest
from src.agents.compliance import compliance_agent
from src.agents.route_optimizer import route_agent
from src.agents.notification import notification_agent
from src.agents.cold_storage import cold_storage_agent
from src.agents.insurance import insurance_agent
from src.agents.inventory import inventory_agent
from src.graph.state import AnomalyRecord
from datetime import datetime


def test_compliance_agent_writes_audit_entry(base_state):
    result = compliance_agent(base_state)
    assert len(result["audit_log"]) >= 1
    entry = result["audit_log"][0]
    assert entry.agent_name == "compliance_agent"
    assert entry.gdp_compliant is True
    assert entry.shipment_id == "SHP-TEST-001"


def test_compliance_agent_marks_gdp_compliant(base_state):
    result = compliance_agent(base_state)
    assert result["gdp_compliant"] is True


def test_route_agent_returns_recommendation(base_state):
    result = route_agent(base_state)
    assert result["route_recommendation"] is not None
    assert result["route_recommendation"].carrier != ""
    assert result["route_recommendation"].risk_score <= 1.0


def test_notification_agent_records_sent(base_state):
    result = notification_agent(base_state)
    assert len(result["notifications_sent"]) > 0
    assert any("Nairobi" in n or "hospital" in n.lower() for n in result["notifications_sent"])


def test_cold_storage_agent_books_facility(base_state):
    result = cold_storage_agent(base_state)
    assert result["cold_storage_booked"] is True
    assert result["cold_storage_facility"] is not None


def test_insurance_agent_generates_claim_id(base_state):
    result = insurance_agent(base_state)
    assert result["insurance_claim_id"] is not None
    assert result["insurance_claim_id"].startswith("CLM-")


def test_inventory_agent_returns_impact(base_state):
    state = {**base_state, "spoilage_probability": 0.5}
    result = inventory_agent(state)
    impact = result["inventory_impact"]
    assert impact is not None
    assert impact["shipment_doses"] > 0
    assert impact["expected_usable_doses"] < impact["shipment_doses"]
    assert "hospital_forecasts" in impact
    assert len(impact["hospital_forecasts"]) > 0


def test_inventory_agent_writes_audit(base_state):
    result = inventory_agent(base_state)
    assert len(result["audit_log"]) == 1
    assert result["audit_log"][0].agent_name == "inventory_agent"
    assert result["audit_log"][0].action_type == "INVENTORY_FORECAST_UPDATED"


def test_inventory_agent_reorder_urgency_high_spoilage(base_state):
    state = {**base_state, "spoilage_probability": 0.9, "severity": "CRITICAL"}
    result = inventory_agent(state)
    assert result["inventory_impact"]["reorder_urgency"] in ("IMMEDIATE", "HIGH")
