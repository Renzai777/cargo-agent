import pytest
from src.simulator.telemetry import TelemetrySimulator


def test_normal_reading_within_vaccine_range():
    sim = TelemetrySimulator(cargo_type="vaccine", shipment_id="SHP-001")
    reading = sim.next_reading()
    assert 1.0 <= reading.temperature_c <= 10.0
    assert reading.shipment_id == "SHP-001"
    assert reading.customs_status == "in_transit"


def test_temp_spike_injection_exceeds_threshold():
    sim = TelemetrySimulator(cargo_type="vaccine", shipment_id="SHP-001")
    reading = sim.next_reading(inject_anomaly="temp_spike")
    assert reading.temperature_c > 8.0


def test_shock_event_injection():
    sim = TelemetrySimulator(cargo_type="vaccine", shipment_id="SHP-001")
    reading = sim.next_reading(inject_anomaly="shock_event")
    assert reading.shock_g > 2.0


def test_customs_hold_at_step_15():
    sim = TelemetrySimulator(cargo_type="vaccine", shipment_id="SHP-001")
    for _ in range(14):
        sim.next_reading()
    reading = sim.next_reading()  # step 15
    assert reading.customs_status == "held"


def test_generate_batch_returns_correct_count():
    sim = TelemetrySimulator(cargo_type="vaccine", shipment_id="SHP-001")
    readings = sim.generate_batch(10)
    assert len(readings) == 10
