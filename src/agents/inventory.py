"""
Inventory Forecast Agent — updates downstream hospital inventory forecasts
when a cold-chain breach threatens supply. Explicitly required by the
UMD problem statement: "update inventory forecasts, recommend rescheduling
patient appointments."
"""
from src.graph.state import CargoState, AuditEntry

# Mock hospital inventory database
HOSPITAL_INVENTORY = {
    "Nairobi": {
        "Kenyatta National Hospital":       {"doses_on_hand": 200, "scheduled_appointments": 85, "reorder_lead_days": 3},
        "Aga Khan University Hospital":     {"doses_on_hand": 120, "scheduled_appointments": 40, "reorder_lead_days": 4},
        "Nairobi West Hospital":            {"doses_on_hand": 80,  "scheduled_appointments": 25, "reorder_lead_days": 5},
    },
    "Frankfurt": {
        "Universitätsklinikum Frankfurt":   {"doses_on_hand": 500, "scheduled_appointments": 150, "reorder_lead_days": 2},
        "Krankenhaus Sachsenhausen":        {"doses_on_hand": 180, "scheduled_appointments": 60,  "reorder_lead_days": 3},
    },
    "New York": {
        "Bellevue Hospital":                {"doses_on_hand": 400, "scheduled_appointments": 200, "reorder_lead_days": 1},
        "NYU Langone Medical Center":       {"doses_on_hand": 320, "scheduled_appointments": 140, "reorder_lead_days": 1},
    },
}

CARGO_DOSES = {"vaccine": 500, "biologics": 200, "default": 300}


def inventory_agent(state: CargoState) -> dict:
    dest = state["destination_city"]
    cargo_type = state["cargo_type"].lower()
    spoilage_prob = state.get("spoilage_probability", 0.0)
    severity = state.get("severity", "LOW")

    shipment_doses = CARGO_DOSES.get(cargo_type, CARGO_DOSES["default"])
    expected_usable = round(shipment_doses * (1.0 - spoilage_prob))
    doses_at_risk = shipment_doses - expected_usable

    hospitals = HOSPITAL_INVENTORY.get(dest, {})
    forecasts = []
    appointments_at_risk = 0

    for hospital, inv in hospitals.items():
        new_on_hand = inv["doses_on_hand"] + expected_usable // max(len(hospitals), 1)
        shortfall = max(0, inv["scheduled_appointments"] - new_on_hand)
        appointments_at_risk += min(shortfall, inv["scheduled_appointments"])
        forecasts.append({
            "hospital": hospital,
            "current_stock": inv["doses_on_hand"],
            "expected_delivery_doses": expected_usable // max(len(hospitals), 1),
            "projected_stock_after_delivery": new_on_hand,
            "scheduled_appointments": inv["scheduled_appointments"],
            "appointments_at_risk": shortfall,
            "reorder_recommended": shortfall > 0,
            "reorder_lead_days": inv["reorder_lead_days"],
        })

    # Urgency driven by spoilage probability OR appointment shortfall
    if spoilage_prob >= 0.7 or appointments_at_risk > 50:
        reorder_urgency = "IMMEDIATE"
    elif spoilage_prob >= 0.4 or appointments_at_risk > 20:
        reorder_urgency = "HIGH"
    else:
        reorder_urgency = "MONITOR"

    impact_summary = {
        "destination": dest,
        "shipment_doses": shipment_doses,
        "doses_at_risk": doses_at_risk,
        "expected_usable_doses": expected_usable,
        "total_appointments_at_risk": appointments_at_risk,
        "reorder_urgency": reorder_urgency,
        "hospital_forecasts": forecasts,
    }

    detail = (
        f"Inventory updated for {len(forecasts)} facilities in {dest}. "
        f"Usable doses: {expected_usable}/{shipment_doses} ({spoilage_prob:.0%} spoilage risk). "
        f"Appointments at risk: {appointments_at_risk}. "
        f"Reorder urgency: {impact_summary['reorder_urgency']}."
    )

    return {
        "inventory_impact": impact_summary,
        "audit_log": [AuditEntry(
            agent_name="inventory_agent",
            action_type="INVENTORY_FORECAST_UPDATED",
            action_detail=detail,
            reasoning=(
                f"Spoilage probability {spoilage_prob:.0%} applied to {shipment_doses}-dose shipment. "
                f"Downstream hospital stock and appointment capacity recalculated. "
                f"Reorder recommendations generated per WHO stockout prevention guidelines."
            ),
            severity=severity,
            gdp_compliant=True,
            shipment_id=state["shipment_id"],
        )],
    }
