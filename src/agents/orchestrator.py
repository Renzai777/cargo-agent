from anthropic import Anthropic
from src.graph.state import CargoState, AuditEntry
from src.agents.demo_responses import ORCHESTRATOR_THINKING_DEMO, ORCHESTRATOR_RESPONSE_DEMO
from src.runtime_config import ANTHROPIC_API_KEY, USE_DEMO_MODE

client = Anthropic(api_key=ANTHROPIC_API_KEY or None)
DEMO_MODE = USE_DEMO_MODE

SYSTEM_PROMPT = """You are the Decision Orchestrator for a pharmaceutical cold-chain monitoring system.
Your job: determine which interventions are required given a risk incident.

Available actions (output these exact strings in your response when applicable):
- REROUTE — recommend alternative route/carrier
- COLD_STORAGE — book emergency cold storage at next airport
- NOTIFY_HOSPITALS — alert destination hospitals to reschedule appointments
- FILE_INSURANCE — initiate insurance claim for potential product loss
- CUSTOMS_ESCALATE — request priority customs clearance

Rules:
1. If spoilage_probability > 0.6: always include REROUTE + COLD_STORAGE
2. If spoilage_probability > 0.4 OR severity == CRITICAL: always include NOTIFY_HOSPITALS
3. If spoilage_probability > 0.7: always include FILE_INSURANCE
4. If customs hold detected: always include CUSTOMS_ESCALATE
5. Regulatory obligation: severity HIGH/CRITICAL requires NOTIFY_HOSPITALS per GDP Article 9.2

Think through the cost-benefit trade-offs carefully before deciding.
Return a clear list of actions and your reasoning."""

ACTION_FLAGS = ["REROUTE", "COLD_STORAGE", "NOTIFY_HOSPITALS", "FILE_INSURANCE", "CUSTOMS_ESCALATE"]


def orchestrator_agent(state: CargoState) -> dict:
    prompt = (
        f"Incident report for shipment {state['shipment_id']}:\n\n"
        f"Cargo: {state['cargo_type']} — {state['cargo_description']}\n"
        f"Route: {state['origin_city']} → {state['destination_city']}\n"
        f"Severity: {state['severity']}\n"
        f"Spoilage probability: {state['spoilage_probability']:.0%}\n"
        f"Delay risk: {state['delay_risk']:.0%}\n"
        f"Anomalies: {[a.description for a in state.get('anomalies', [])]}\n"
    )

    # Add predictive data if available
    breach_mins = state.get("predicted_breach_minutes")
    if breach_mins is not None:
        prompt += f"Predicted temperature breach: in {breach_mins:.0f} minutes\n"

    prompt += "\nList required actions (use exact action names) and explain your reasoning."

    # Demo mode: use pre-scripted responses (no API key needed)
    if DEMO_MODE:
        actions = [a for a in ACTION_FLAGS if a in ORCHESTRATOR_RESPONSE_DEMO]
        return {
            "recommended_actions": actions,
            "orchestrator_reasoning": ORCHESTRATOR_RESPONSE_DEMO,
            "orchestrator_thinking": ORCHESTRATOR_THINKING_DEMO,
            "awaiting_human_approval": False,
            "audit_log": [AuditEntry(
                agent_name="orchestrator_agent",
                action_type="INTERVENTION_DECISION",
                action_detail=f"[DEMO] Actions decided: {', '.join(actions)}",
                reasoning=ORCHESTRATOR_RESPONSE_DEMO[:500],
                severity=state.get("severity", "LOW"),
                gdp_compliant=True,
                shipment_id=state["shipment_id"],
            )],
        }

    thinking_text = ""
    try:
        # Extended thinking — Claude deliberates before deciding (requires claude-sonnet-4-6+)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=16000,
            thinking={"type": "enabled", "budget_tokens": 10000},
            system=[{
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": prompt}],
        )
        thinking_text = next(
            (b.thinking for b in response.content if b.type == "thinking"), ""
        )
        response_text = next(
            (b.text for b in response.content if b.type == "text"), ""
        )
    except Exception:
        # Fallback: standard call without extended thinking
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=[{
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": prompt}],
        )
        response_text = response.content[0].text

    actions = [a for a in ACTION_FLAGS if a in response_text]

    return {
        "recommended_actions": actions,
        "orchestrator_reasoning": response_text,
        "orchestrator_thinking": thinking_text,
        "awaiting_human_approval": False,
        "audit_log": [AuditEntry(
            agent_name="orchestrator_agent",
            action_type="INTERVENTION_DECISION",
            action_detail=f"Actions decided: {', '.join(actions) or 'MONITOR_ONLY'}",
            reasoning=response_text[:500],
            severity=state.get("severity", "LOW"),
            gdp_compliant=True,
            shipment_id=state["shipment_id"],
        )],
    }
