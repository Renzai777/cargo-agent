import sqlite3
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Send
from src.graph.state import CargoState
from src.agents.monitor import monitor_agent
from src.agents.predictor import predictor_agent
from src.agents.anomaly_detector import anomaly_agent
from src.agents.risk_assessor import risk_agent
from src.agents.orchestrator import orchestrator_agent
from src.agents.route_optimizer import route_agent
from src.agents.notification import notification_agent
from src.agents.inventory import inventory_agent
from src.agents.cold_storage import cold_storage_agent
from src.agents.insurance import insurance_agent
from src.agents.compliance import compliance_agent


def _route_after_risk(state: CargoState) -> str:
    severity = state.get("severity", "LOW")
    if severity in ("HIGH", "CRITICAL", "MEDIUM"):
        return "decision_orchestrator"
    return "compliance_agent"


def _route_orchestrator(state: CargoState) -> list[Send]:
    actions = state.get("recommended_actions", [])
    sends = []
    if "REROUTE" in actions:
        sends.append(Send("route_optimizer", state))
    if "NOTIFY_HOSPITALS" in actions:
        sends.append(Send("notification_agent", state))
        sends.append(Send("inventory_agent", state))  # always update inventory alongside notifications
    if "COLD_STORAGE" in actions:
        sends.append(Send("cold_storage_agent", state))
    if "FILE_INSURANCE" in actions:
        sends.append(Send("insurance_agent", state))
    sends.append(Send("compliance_agent", state))
    return sends if sends else [Send("compliance_agent", state)]


def build_graph(db_path: str = "cargo.db") -> StateGraph:
    builder = StateGraph(CargoState)

    # Detection pipeline — predictor runs first to forecast breach before anomaly analysis
    builder.add_node("monitor_agent", monitor_agent)
    builder.add_node("predictor_agent", predictor_agent)
    builder.add_node("anomaly_agent", anomaly_agent)
    builder.add_node("risk_agent", risk_agent)

    # Decision + action agents
    builder.add_node("decision_orchestrator", orchestrator_agent)
    builder.add_node("route_optimizer", route_agent)
    builder.add_node("notification_agent", notification_agent)
    builder.add_node("inventory_agent", inventory_agent)
    builder.add_node("cold_storage_agent", cold_storage_agent)
    builder.add_node("insurance_agent", insurance_agent)
    builder.add_node("compliance_agent", compliance_agent)

    # Detection pipeline edges
    builder.add_edge(START, "monitor_agent")
    builder.add_edge("monitor_agent", "predictor_agent")
    builder.add_edge("predictor_agent", "anomaly_agent")
    builder.add_edge("anomaly_agent", "risk_agent")

    # Risk → orchestrator (medium/high/critical) or log-only (low)
    builder.add_conditional_edges("risk_agent", _route_after_risk, {
        "decision_orchestrator": "decision_orchestrator",
        "compliance_agent": "compliance_agent",
    })

    # Orchestrator → parallel action agents (fan-out via Send)
    builder.add_conditional_edges("decision_orchestrator", _route_orchestrator)

    # All action agents terminate the graph
    for node in ["route_optimizer", "notification_agent", "inventory_agent",
                 "cold_storage_agent", "insurance_agent", "compliance_agent"]:
        builder.add_edge(node, END)

    conn = sqlite3.connect(db_path, check_same_thread=False)
    checkpointer = SqliteSaver(conn)

    return builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["decision_orchestrator"]
    )
