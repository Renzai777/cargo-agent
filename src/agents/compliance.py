from src.graph.state import CargoState, AuditEntry
from src.tools.compliance_rules import get_gdp_threshold, is_gdp_compliant


def compliance_agent(state: CargoState) -> dict:
    reading = state.get("latest_reading")
    cargo_type = state["cargo_type"]

    gdp_ok = True
    if reading:
        gdp_ok = is_gdp_compliant(cargo_type, reading.temperature_c)

    actions_summary = ", ".join(state.get("recommended_actions", [])) or "MONITOR_ONLY"
    thresholds = get_gdp_threshold(cargo_type)

    detail = (
        f"Incident logged. Severity: {state.get('severity', 'LOW')}. "
        f"Actions triggered: {actions_summary}. "
        f"GDP thresholds for {cargo_type}: {thresholds['temp_min']}–{thresholds['temp_max']}°C. "
        f"Compliance status: {'COMPLIANT' if gdp_ok else 'BREACH — excursion logged per GDP Art.9.2'}"
    )

    reasoning = (
        f"Orchestrator reasoning: {state.get('orchestrator_reasoning', 'N/A')[:200]}. "
        f"Audit entry generated per FDA 21 CFR Part 11 requirements."
    )

    return {
        "gdp_compliant": gdp_ok,
        "audit_log": [AuditEntry(
            agent_name="compliance_agent",
            action_type="COMPLIANCE_LOG",
            action_detail=detail,
            reasoning=reasoning,
            severity=state.get("severity", "LOW"),
            gdp_compliant=gdp_ok,
            shipment_id=state["shipment_id"],
        )],
    }
