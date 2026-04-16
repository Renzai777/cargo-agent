# tests/conftest.py
import pytest
from datetime import datetime


@pytest.fixture
def sample_reading():
    from src.graph.state import TelemetryReading
    return TelemetryReading(
        shipment_id="SHP-TEST-001",
        timestamp=datetime(2026, 4, 16, 12, 0, 0),
        temperature_c=4.5,
        humidity_pct=55.0,
        shock_g=0.3,
        latitude=40.7128,
        longitude=-74.0060,
        altitude_m=0.0,
        customs_status="in_transit",
        carrier_id="CARRIER_DHL_001"
    )


@pytest.fixture
def spike_reading():
    from src.graph.state import TelemetryReading
    return TelemetryReading(
        shipment_id="SHP-TEST-001",
        timestamp=datetime(2026, 4, 16, 14, 0, 0),
        temperature_c=16.5,
        humidity_pct=55.0,
        shock_g=0.3,
        latitude=50.0,
        longitude=8.0,
        altitude_m=35000.0,
        customs_status="in_transit",
        carrier_id="CARRIER_DHL_001"
    )


@pytest.fixture
def base_state(sample_reading):
    from datetime import datetime
    return {
        "shipment_id": "SHP-TEST-001",
        "cargo_type": "vaccine",
        "cargo_description": "COVID-19 mRNA Vaccine — 500 doses",
        "origin_city": "New York",
        "destination_city": "Nairobi",
        "expected_arrival": datetime(2026, 4, 17, 10, 0, 0),
        "telemetry_window": [sample_reading],
        "latest_reading": sample_reading,
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
