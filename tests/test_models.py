import pytest
from datetime import datetime
from src.graph.state import TelemetryReading, AnomalyRecord, AuditEntry, CargoState


def test_telemetry_reading_valid():
    r = TelemetryReading(
        shipment_id="SHP-001",
        timestamp=datetime(2026, 4, 16, 12, 0),
        temperature_c=4.5,
        humidity_pct=55.0,
        shock_g=0.3,
        latitude=40.71,
        longitude=-74.00,
        altitude_m=0.0,
        customs_status="in_transit",
        carrier_id="DHL-001"
    )
    assert r.temperature_c == 4.5
    assert r.customs_status == "in_transit"


def test_anomaly_record_severity_values():
    a = AnomalyRecord(
        anomaly_id="ANO-001",
        shipment_id="SHP-001",
        timestamp=datetime(2026, 4, 16, 12, 0),
        anomaly_type="temp_excursion",
        severity="CRITICAL",
        z_score=4.2,
        description="Temperature 16.5°C exceeds 8°C max threshold",
        raw_value=16.5,
        threshold_value=8.0
    )
    assert a.severity == "CRITICAL"
    assert a.z_score == 4.2


def test_cargo_state_is_dict_compatible(base_state):
    assert base_state["shipment_id"] == "SHP-TEST-001"
    assert base_state["severity"] == "LOW"
    assert base_state["anomalies"] == []
