from src.graph.state import CargoState, AuditEntry
from src.tools.claims import file_insurance_claim

CARGO_VALUES = {"vaccine": 85000.0, "biologics": 120000.0, "default": 50000.0}


def insurance_agent(state: CargoState) -> dict:
    value = CARGO_VALUES.get(state["cargo_type"].lower(), CARGO_VALUES["default"])
    estimated_loss = value * state.get("spoilage_probability", 0.5)
    anomaly_desc = "; ".join(a.description for a in state.get("anomalies", []))
    claim = file_insurance_claim(state["shipment_id"], anomaly_desc, estimated_loss)

    return {
        "insurance_claim_id": claim["claim_id"],
        "audit_log": [AuditEntry(
            agent_name="insurance_agent",
            action_type="INSURANCE_CLAIM_FILED",
            action_detail=f"Claim {claim['claim_id']} filed — estimated loss ${estimated_loss:,.0f}",
            reasoning=f"Automatic claim per policy terms for cold-chain breach with spoilage probability {state.get('spoilage_probability', 0):.0%}",
            severity=state.get("severity", "LOW"),
            gdp_compliant=True,
            shipment_id=state["shipment_id"],
        )],
    }
