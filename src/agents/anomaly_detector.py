import json
from datetime import datetime
import numpy as np
from anthropic import Anthropic
from src.graph.state import CargoState, AnomalyRecord, AuditEntry

client = Anthropic()
Z_SCORE_THRESHOLD = 3.0


def anomaly_agent(state: CargoState) -> dict:
    window = state["telemetry_window"][-20:]
    reading = state["latest_reading"]

    if len(window) < 3:
        return {"anomalies": [], "audit_log": [_audit("Insufficient window for analysis", state)]}

    temps = [r.temperature_c for r in window]
    mean = float(np.mean(temps))
    std = float(np.std(temps))

    if std < 0.001:
        return {"anomalies": [], "audit_log": [_audit("Zero variance in window — nominal", state)]}

    z_score = abs((reading.temperature_c - mean) / std)

    if z_score < Z_SCORE_THRESHOLD:
        return {"anomalies": [], "audit_log": [_audit(f"Z-score {z_score:.2f} below threshold", state)]}

    ANOMALY_SYSTEM = (
        "You are an anomaly classification engine for pharmaceutical cold-chain logistics. "
        "You receive temperature sensor data and classify anomalies for GDP/FDA compliance. "
        "Always return ONLY valid JSON with keys: severity, description, anomaly_type."
    )

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        # Prompt caching — system prompt cached across repeated anomaly calls
        system=[{
            "type": "text",
            "text": ANOMALY_SYSTEM,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{
            "role": "user",
            "content": (
                f"Analyze this temperature anomaly for pharmaceutical cargo:\n\n"
                f"Cargo: {state['cargo_type']} ({state['cargo_description']})\n"
                f"Current temp: {reading.temperature_c}°C\n"
                f"Window mean: {mean:.2f}°C, std: {std:.2f}°C\n"
                f"Z-score: {z_score:.2f}\n"
                f"Customs status: {reading.customs_status}\n"
                f"Location: {reading.latitude:.2f}, {reading.longitude:.2f}\n"
                f"Altitude: {reading.altitude_m}m\n\n"
                f"Classify severity (LOW/MEDIUM/HIGH/CRITICAL) and explain in 2 sentences.\n"
                f"Return ONLY valid JSON: "
                f'{{"severity": "...", "description": "...", "anomaly_type": "..."}}'
            )
        }]
    )

    result = json.loads(response.content[0].text.strip())
    anomaly = AnomalyRecord(
        shipment_id=state["shipment_id"],
        anomaly_type=result["anomaly_type"],
        severity=result["severity"],
        z_score=round(z_score, 2),
        description=result["description"],
        raw_value=reading.temperature_c,
        threshold_value=8.0 if state["cargo_type"] == "vaccine" else 25.0,
    )

    return {
        "anomalies": [anomaly],
        "audit_log": [_audit(
            f"Z-score {z_score:.2f} — LLM classified as {result['severity']}: {result['description'][:80]}",
            state
        )],
    }


def _audit(detail: str, state: CargoState) -> AuditEntry:
    return AuditEntry(
        agent_name="anomaly_agent",
        action_type="ANOMALY_ANALYSIS",
        action_detail=detail,
        reasoning="Statistical Z-score analysis + LLM contextual classification",
        severity="INFO",
        gdp_compliant=True,
        shipment_id=state["shipment_id"],
    )
