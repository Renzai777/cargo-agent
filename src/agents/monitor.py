from datetime import datetime
from src.graph.state import CargoState, AnomalyRecord, AuditEntry

THRESHOLDS: dict[str, dict] = {
    "vaccine":   {"temp_min": 2.0, "temp_max": 8.0, "humidity_max": 75.0, "shock_max": 2.0},
    "biologics": {"temp_min": -20.0, "temp_max": -15.0, "humidity_max": 60.0, "shock_max": 1.5},
    "default":   {"temp_min": 2.0, "temp_max": 25.0, "humidity_max": 80.0, "shock_max": 3.0},
}


def monitor_agent(state: CargoState) -> dict:
    reading = state["latest_reading"]
    cargo_type = state["cargo_type"].lower()
    t = THRESHOLDS.get(cargo_type, THRESHOLDS["default"])
    anomalies: list[AnomalyRecord] = []

    if not (t["temp_min"] <= reading.temperature_c <= t["temp_max"]):
        anomalies.append(AnomalyRecord(
            shipment_id=state["shipment_id"],
            anomaly_type="temp_excursion",
            severity="HIGH",
            description=(
                f"Temperature {reading.temperature_c}°C outside safe range "
                f"[{t['temp_min']}, {t['temp_max']}]°C for {cargo_type}"
            ),
            raw_value=reading.temperature_c,
            threshold_value=t["temp_max"] if reading.temperature_c > t["temp_max"] else t["temp_min"],
        ))

    if reading.humidity_pct > t["humidity_max"]:
        anomalies.append(AnomalyRecord(
            shipment_id=state["shipment_id"],
            anomaly_type="humidity_excursion",
            severity="MEDIUM",
            description=f"Humidity {reading.humidity_pct}% exceeds {t['humidity_max']}% max",
            raw_value=reading.humidity_pct,
            threshold_value=t["humidity_max"],
        ))

    if reading.shock_g > t["shock_max"]:
        anomalies.append(AnomalyRecord(
            shipment_id=state["shipment_id"],
            anomaly_type="shock_event",
            severity="MEDIUM",
            description=f"Shock {reading.shock_g}g exceeds {t['shock_max']}g max",
            raw_value=reading.shock_g,
            threshold_value=t["shock_max"],
        ))

    if reading.customs_status == "held":
        anomalies.append(AnomalyRecord(
            shipment_id=state["shipment_id"],
            anomaly_type="customs_hold",
            severity="HIGH",
            description="Shipment held at customs — potential delay to destination",
            raw_value=0.0,
            threshold_value=0.0,
        ))

    detail = f"Detected {len(anomalies)} breach(es)" if anomalies else "All thresholds nominal"
    return {
        "anomalies": anomalies,
        "audit_log": [AuditEntry(
            agent_name="monitor_agent",
            action_type="THRESHOLD_CHECK",
            action_detail=detail,
            reasoning=f"Compared reading against GDP thresholds for cargo type '{cargo_type}'",
            severity="HIGH" if anomalies else "LOW",
            gdp_compliant=True,
            shipment_id=state["shipment_id"],
        )],
    }
