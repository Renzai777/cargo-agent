"""Pre-defined failure scenario scripts used for demo and testing."""
from src.simulator.telemetry import TelemetrySimulator
from src.graph.state import TelemetryReading


def scenario_temp_spike(shipment_id: str = "SHP-DEMO-001") -> list[TelemetryReading]:
    """30 readings across the full route; spike injected at step 20 (Frankfurt leg)."""
    sim = TelemetrySimulator("vaccine", shipment_id, total_steps=30)
    readings = sim.generate_batch(19)
    readings.append(sim.next_reading(inject_anomaly="temp_spike"))
    readings += sim.generate_batch(10)
    return readings


def scenario_customs_hold(shipment_id: str = "SHP-DEMO-002") -> list[TelemetryReading]:
    """30 readings; customs hold visible around Frankfurt (steps 15-20)."""
    sim = TelemetrySimulator("vaccine", shipment_id, total_steps=30)
    return sim.generate_batch(30)


def scenario_gradual_drift(shipment_id: str = "SHP-DEMO-003") -> list[TelemetryReading]:
    """30 readings; temperature gradually drifts from step 10 onward."""
    sim = TelemetrySimulator("vaccine", shipment_id, total_steps=30)
    return sim.generate_batch(30, inject_at={i: "gradual_drift" for i in range(10, 30)})


def scenario_compound_failure(shipment_id: str = "SHP-DEMO-004") -> list[TelemetryReading]:
    """30 readings; temperature spike mid-route then customs hold near Frankfurt."""
    sim = TelemetrySimulator("vaccine", shipment_id, total_steps=30)
    readings = sim.generate_batch(14)
    readings.append(sim.next_reading(inject_anomaly="temp_spike"))
    readings += sim.generate_batch(15)
    return readings


SCENARIOS = {
    "temp_spike": scenario_temp_spike,
    "customs_hold": scenario_customs_hold,
    "gradual_drift": scenario_gradual_drift,
    "compound_failure": scenario_compound_failure,
}
