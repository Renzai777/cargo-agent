from src.graph.state import CargoState, AuditEntry
from src.tools.storage import find_cold_storage, book_cold_storage


def cold_storage_agent(state: CargoState) -> dict:
    reading = state.get("latest_reading")
    location = f"{reading.latitude:.1f},{reading.longitude:.1f}" if reading else "unknown"
    facilities = find_cold_storage(location, state["cargo_type"])
    best = facilities["facilities"][0]
    booking = book_cold_storage(best["id"], state["shipment_id"], duration_hours=48)

    return {
        "cold_storage_booked": True,
        "cold_storage_facility": booking["facility"],
        "audit_log": [AuditEntry(
            agent_name="cold_storage_agent",
            action_type="COLD_STORAGE_BOOKED",
            action_detail=f"Booked {booking['facility']} for 48h emergency storage",
            reasoning=f"Spoilage risk {state.get('spoilage_probability', 0):.0%} requires immediate cold storage intervention",
            severity=state.get("severity", "LOW"),
            gdp_compliant=True,
            shipment_id=state["shipment_id"],
        )],
    }
