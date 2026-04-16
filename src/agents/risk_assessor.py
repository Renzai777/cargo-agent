import json
from anthropic import Anthropic
from src.graph.state import CargoState, AuditEntry
from src.tools.spoilage import calculate_spoilage_probability
from src.tools.routing import get_route_eta
from src.agents.demo_responses import RISK_DEMO
from src.runtime_config import ANTHROPIC_API_KEY, USE_DEMO_MODE

client = Anthropic(api_key=ANTHROPIC_API_KEY or None)
DEMO_MODE = USE_DEMO_MODE

RISK_TOOLS = [
    {
        "name": "calculate_spoilage_probability",
        "description": "Estimates vaccine/biologics spoilage probability given temperature excursion details",
        "input_schema": {
            "type": "object",
            "properties": {
                "cargo_type": {"type": "string", "description": "e.g. vaccine, biologics"},
                "temp_excursion_c": {"type": "number", "description": "Degrees above max safe threshold"},
                "duration_minutes": {"type": "number", "description": "Estimated excursion duration so far"},
            },
            "required": ["cargo_type", "temp_excursion_c", "duration_minutes"],
        },
    },
    {
        "name": "get_route_eta",
        "description": "Returns remaining route time in minutes for a given shipment",
        "input_schema": {
            "type": "object",
            "properties": {
                "shipment_id": {"type": "string"},
            },
            "required": ["shipment_id"],
        },
    },
]


def _run_tool(name: str, inputs: dict) -> str:
    if name == "calculate_spoilage_probability":
        result = calculate_spoilage_probability(**inputs)
        return json.dumps({"spoilage_probability": result})
    if name == "get_route_eta":
        result = get_route_eta(**inputs)
        return json.dumps(result)
    return json.dumps({"error": f"Unknown tool: {name}"})


def risk_agent(state: CargoState) -> dict:
    if not state.get("anomalies"):
        return {
            "spoilage_probability": 0.0,
            "delay_risk": 0.0,
            "severity": "LOW",
            "audit_log": [AuditEntry(
                agent_name="risk_agent",
                action_type="RISK_ASSESSMENT",
                action_detail="No anomalies detected — risk is LOW",
                reasoning="No anomaly records in state",
                severity="LOW",
                gdp_compliant=True,
                shipment_id=state["shipment_id"],
            )],
        }

    # Demo mode: skip real API call, use pre-scripted response
    if DEMO_MODE:
        result = RISK_DEMO
        return {
            "spoilage_probability": result["spoilage_probability"],
            "delay_risk": result["delay_risk"],
            "severity": result["severity"],
            "audit_log": [AuditEntry(
                agent_name="risk_agent",
                action_type="RISK_ASSESSMENT",
                action_detail=f"[DEMO] Spoilage: {result['spoilage_probability']:.0%}, Delay: {result['delay_risk']:.0%}",
                reasoning=result["reasoning"],
                severity=result["severity"],
                gdp_compliant=True,
                shipment_id=state["shipment_id"],
            )],
        }

    RISK_SYSTEM = (
        "You are a pharmaceutical cold-chain risk assessment specialist. "
        "Use the provided tools to calculate spoilage probability and route ETA, "
        "then return a JSON risk report. Be precise and use tool outputs in your scoring."
    )

    messages = [{
        "role": "user",
        "content": (
            f"Assess spoilage and delay risk for this pharmaceutical shipment:\n\n"
            f"Shipment: {state['shipment_id']} | {state['cargo_type']}: {state['cargo_description']}\n"
            f"Route: {state['origin_city']} → {state['destination_city']}\n"
            f"Anomalies: {[a.description for a in state['anomalies']]}\n"
            f"Temp: {state['latest_reading'].temperature_c if state['latest_reading'] else 'N/A'}°C\n\n"
            f"Use available tools to calculate spoilage probability and route ETA, then return JSON:\n"
            f'{{"spoilage_probability": 0.0-1.0, "delay_risk": 0.0-1.0, "severity": "LOW|MEDIUM|HIGH|CRITICAL", "reasoning": "..."}}'
        ),
    }]

    for _ in range(5):
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            # Prompt caching — system prompt + tool definitions cached
            system=[{
                "type": "text",
                "text": RISK_SYSTEM,
                "cache_control": {"type": "ephemeral"},
            }],
            tools=RISK_TOOLS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            text = next((b.text for b in response.content if hasattr(b, "text")), "{}")
            result = json.loads(text)
            return {
                "spoilage_probability": float(result.get("spoilage_probability", 0.0)),
                "delay_risk": float(result.get("delay_risk", 0.0)),
                "severity": result.get("severity", "LOW"),
                "audit_log": [AuditEntry(
                    agent_name="risk_agent",
                    action_type="RISK_ASSESSMENT",
                    action_detail=f"Spoilage: {result.get('spoilage_probability', 0):.0%}, Delay: {result.get('delay_risk', 0):.0%}",
                    reasoning=result.get("reasoning", ""),
                    severity=result.get("severity", "LOW"),
                    gdp_compliant=True,
                    shipment_id=state["shipment_id"],
                )],
            }

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                output = _run_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output,
                })

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

    return {"spoilage_probability": 0.5, "delay_risk": 0.5, "severity": "HIGH", "audit_log": []}
