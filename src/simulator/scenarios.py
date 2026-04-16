"""Pre-defined failure scenario scripts used for demo and testing."""
from src.simulator.telemetry import TelemetrySimulator
from src.graph.state import TelemetryReading


def scenario_temp_spike(shipment_id: str = "SHP-DEMO-001") -> list[TelemetryReading]:
    """10 normal readings, then a temperature spike at step 11."""
    sim = TelemetrySimulator("vaccine", shipment_id)
    readings = sim.generate_batch(10)
    readings.append(sim.next_reading(inject_anomaly="temp_spike"))
    return readings


def scenario_customs_hold(shipment_id: str = "SHP-DEMO-002") -> list[TelemetryReading]:
    """Customs hold kicks in around step 15."""
    sim = TelemetrySimulator("vaccine", shipment_id)
    return sim.generate_batch(22)


def scenario_gradual_drift(shipment_id: str = "SHP-DEMO-003") -> list[TelemetryReading]:
    """Temperature gradually drifts up over 20 steps."""
    sim = TelemetrySimulator("vaccine", shipment_id)
    return sim.generate_batch(20, inject_at={i: "gradual_drift" for i in range(5, 20)})


def scenario_compound_failure(shipment_id: str = "SHP-DEMO-004") -> list[TelemetryReading]:
    """Temperature spike AND customs hold simultaneously."""
    sim = TelemetrySimulator("vaccine", shipment_id, total_steps=50)
    readings = sim.generate_batch(14)
    readings.append(sim.next_reading(inject_anomaly="temp_spike"))
    readings += sim.generate_batch(5)
    return readings


SCENARIOS = {
    "temp_spike": scenario_temp_spike,
    "customs_hold": scenario_customs_hold,
    "gradual_drift": scenario_gradual_drift,
    "compound_failure": scenario_compound_failure,
}
