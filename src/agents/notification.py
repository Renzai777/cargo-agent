from src.graph.state import CargoState, AuditEntry

DESTINATION_HOSPITALS = {
    "Nairobi": ["Kenyatta National Hospital", "Aga Khan University Hospital", "Nairobi West Hospital"],
    "Frankfurt": ["Universitätsklinikum Frankfurt", "Krankenhaus Sachsenhausen"],
    "New York": ["Bellevue Hospital", "NYU Langone Medical Center"],
}


def notification_agent(state: CargoState) -> dict:
    dest = state["destination_city"]
    hospitals = DESTINATION_HOSPITALS.get(dest, [f"{dest} General Hospital"])
    severity = state.get("severity", "LOW")

    notifications = []
    for h in hospitals:
        msg = (
            f"ALERT [{severity}]: Shipment {state['shipment_id']} carrying "
            f"{state['cargo_type']} may be delayed or compromised. "
            f"Spoilage probability: {state.get('spoilage_probability', 0):.0%}. "
            f"Please prepare contingency stock and reschedule non-urgent appointments."
        )
        notifications.append(f"Notified {h}: {msg[:100]}")

    return {
        "notifications_sent": notifications,
        "audit_log": [AuditEntry(
            agent_name="notification_agent",
            action_type="HOSPITAL_NOTIFICATION",
            action_detail=f"Notified {len(notifications)} facilities in {dest}",
            reasoning="GDP Art.9.2 requires downstream notification when cold-chain breach severity >= HIGH",
            severity=severity,
            gdp_compliant=True,
            shipment_id=state["shipment_id"],
        )],
    }
