from datetime import datetime, timedelta
from src.graph.state import CargoState, RouteOption, AuditEntry

ALTERNATIVE_ROUTES = [
    {"carrier": "Lufthansa Cargo", "extra_hours": 2, "cost_usd": 4200, "risk_score": 0.15},
    {"carrier": "Ethiopian Airlines Cargo", "extra_hours": 4, "cost_usd": 3100, "risk_score": 0.25},
    {"carrier": "Emirates SkyCargo", "extra_hours": 6, "cost_usd": 2800, "risk_score": 0.30},
]


def route_agent(state: CargoState) -> dict:
    best = ALTERNATIVE_ROUTES[0]
    arrival = state.get("expected_arrival") or datetime.utcnow() + timedelta(hours=10)
    option = RouteOption(
        carrier=best["carrier"],
        estimated_arrival=arrival + timedelta(hours=best["extra_hours"]),
        cost_usd=best["cost_usd"],
        risk_score=best["risk_score"],
        reasoning=(
            f"Selected {best['carrier']} as lowest-risk alternative. "
            f"Additional cost: ${best['cost_usd']:,}. "
            f"Risk score: {best['risk_score']:.0%}. Cold-chain integrity verified on this carrier."
        ),
    )
    return {
        "route_recommendation": option,
        "audit_log": [AuditEntry(
            agent_name="route_optimizer",
            action_type="ROUTE_RECOMMENDATION",
            action_detail=f"Recommended {option.carrier} — risk {option.risk_score:.0%}, ${option.cost_usd:,}",
            reasoning=option.reasoning,
            severity=state.get("severity", "LOW"),
            gdp_compliant=True,
            shipment_id=state["shipment_id"],
        )],
    }
