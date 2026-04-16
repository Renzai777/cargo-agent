from __future__ import annotations
from datetime import datetime
from typing import Literal
import numpy as np
from src.graph.state import TelemetryReading

BASELINES: dict[str, dict] = {
    "vaccine":   {"temp": 4.5, "humidity": 55.0, "shock": 0.3, "temp_min": 2.0, "temp_max": 8.0},
    "biologics": {"temp": -18.0, "humidity": 40.0, "shock": 0.2, "temp_min": -20.0, "temp_max": -15.0},
    "default":   {"temp": 4.5, "humidity": 55.0, "shock": 0.3, "temp_min": 2.0, "temp_max": 25.0},
}

# NYC → Frankfurt → Nairobi waypoints
LAT_WAYPOINTS = [40.7128, 50.1109, -1.2921]
LON_WAYPOINTS = [-74.0060, 8.6821, 36.8219]
ALT_WAYPOINTS = [0.0, 35000.0, 0.0]


class TelemetrySimulator:
    def __init__(self, cargo_type: str, shipment_id: str, total_steps: int = 100):
        self.cargo_type = cargo_type.lower()
        self.shipment_id = shipment_id
        self.total_steps = total_steps
        self._step = 0
        self._baseline = BASELINES.get(self.cargo_type, BASELINES["default"])

    def next_reading(
        self,
        inject_anomaly: Literal["temp_spike", "gradual_drift", "shock_event", "humidity_surge"] | None = None
    ) -> TelemetryReading:
        self._step += 1
        b = self._baseline

        temp = b["temp"] + np.random.normal(0, 0.3)
        humidity = b["humidity"] + np.random.normal(0, 1.5)
        shock = max(0.0, b["shock"] + np.random.exponential(0.05))

        if inject_anomaly == "temp_spike":
            temp = b["temp_max"] + np.random.uniform(5.0, 12.0)
        elif inject_anomaly == "gradual_drift":
            temp = b["temp"] + (self._step * 0.08)
        elif inject_anomaly == "shock_event":
            shock = np.random.uniform(3.5, 6.0)
        elif inject_anomaly == "humidity_surge":
            humidity = np.random.uniform(85.0, 95.0)

        return TelemetryReading(
            shipment_id=self.shipment_id,
            timestamp=datetime.utcnow(),
            temperature_c=round(float(temp), 2),
            humidity_pct=round(float(np.clip(humidity, 0.0, 100.0)), 1),
            shock_g=round(float(shock), 3),
            latitude=round(self._interpolate(LAT_WAYPOINTS), 4),
            longitude=round(self._interpolate(LON_WAYPOINTS), 4),
            altitude_m=round(self._interpolate(ALT_WAYPOINTS), 0),
            customs_status=self._customs_status(),
            carrier_id="CARRIER_DHL_001"
        )

    def generate_batch(self, count: int, inject_at: dict[int, str] | None = None) -> list[TelemetryReading]:
        inject_at = inject_at or {}
        return [self.next_reading(inject_anomaly=inject_at.get(i)) for i in range(count)]

    def _interpolate(self, waypoints: list[float]) -> float:
        progress = min(self._step / self.total_steps, 1.0)
        n = len(waypoints) - 1
        idx = min(int(progress * n), n - 1)
        t = (progress * n) - idx
        return waypoints[idx] + t * (waypoints[idx + 1] - waypoints[idx])

    def _customs_status(self) -> str:
        if 15 <= self._step <= 20:
            return "held"
        return "in_transit"
