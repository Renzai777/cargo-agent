# Low Level Design (LLD) — AI Cargo Monitor
**UMD Agentic AI Hackathon 2026 · Case 6**

---

## 1. Data Models (Pydantic v2)

```python
# src/graph/state.py

from typing import TypedDict, Literal, Annotated
from pydantic import BaseModel
from datetime import datetime
import operator

class TelemetryReading(BaseModel):
    shipment_id: str
    timestamp: datetime
    temperature_c: float          # Celsius — valid range 2.0–8.0 for vaccines
    humidity_pct: float           # 0–100
    shock_g: float                # g-force — alert if > 2.0
    latitude: float
    longitude: float
    altitude_m: float
    customs_status: str           # "in_transit" | "held" | "cleared"
    carrier_id: str

class AnomalyRecord(BaseModel):
    anomaly_id: str
    shipment_id: str
    timestamp: datetime
    anomaly_type: str             # "temp_excursion" | "humidity" | "shock" | "delay"
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    z_score: float | None
    description: str              # LLM-generated natural language description
    raw_value: float
    threshold_value: float

class RouteOption(BaseModel):
    route_id: str
    carrier: str
    estimated_arrival: datetime
    cost_usd: float
    risk_score: float             # 0–1 (lower is better)
    reasoning: str

class AuditEntry(BaseModel):
    entry_id: str
    timestamp: datetime
    agent_name: str
    action_type: str
    action_detail: str
    reasoning: str                # Claude's chain-of-thought
    severity: str
    gdp_compliant: bool
    shipment_id: str

class CargoState(TypedDict):
    # Identity
    shipment_id: str
    cargo_type: str
    cargo_description: str
    origin_city: str
    destination_city: str
    expected_arrival: datetime
    
    # Telemetry (append-only via operator.add)
    telemetry_window: Annotated[list[TelemetryReading], operator.add]
    latest_reading: TelemetryReading | None
    
    # Detection
    anomalies: Annotated[list[AnomalyRecord], operator.add]
    spoilage_probability: float      # 0.0–1.0
    delay_risk: float                # 0.0–1.0
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    
    # Decision
    recommended_actions: list[str]
    orchestrator_reasoning: str
    
    # Action results
    route_recommendation: RouteOption | None
    notifications_sent: Annotated[list[str], operator.add]
    cold_storage_booked: bool
    cold_storage_facility: str | None
    insurance_claim_id: str | None
    
    # Compliance
    audit_log: Annotated[list[AuditEntry], operator.add]
    gdp_compliant: bool
    
    # HITL
    awaiting_human_approval: bool
    human_decision: Literal["approved", "rejected", "modified"] | None
    human_notes: str | None
```

---

## 2. LangGraph Graph Definition

```python
# src/graph/cargo_graph.py

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Send
from src.graph.state import CargoState
from src.agents import (
    monitor_agent, anomaly_agent, risk_agent,
    orchestrator_agent, route_agent, notification_agent,
    cold_storage_agent, insurance_agent, compliance_agent
)

def should_escalate(state: CargoState) -> str:
    """Route after risk assessment."""
    if state["severity"] in ("HIGH", "CRITICAL"):
        return "awaiting_hitl"
    elif state["severity"] == "MEDIUM":
        return "decision_orchestrator"
    else:
        return "compliance_agent"   # LOW: log only

def route_orchestrator(state: CargoState) -> list[Send]:
    """Fan out to action agents based on recommended_actions."""
    sends = []
    actions = state["recommended_actions"]
    if "REROUTE" in actions:
        sends.append(Send("route_optimizer", state))
    if "NOTIFY_HOSPITALS" in actions:
        sends.append(Send("notification_agent", state))
    if "COLD_STORAGE" in actions:
        sends.append(Send("cold_storage_agent", state))
    if "FILE_INSURANCE" in actions:
        sends.append(Send("insurance_agent", state))
    sends.append(Send("compliance_agent", state))   # always
    return sends

def build_graph(db_path: str = "cargo.db") -> StateGraph:
    builder = StateGraph(CargoState)

    # Register nodes
    builder.add_node("monitor_agent", monitor_agent)
    builder.add_node("anomaly_agent", anomaly_agent)
    builder.add_node("risk_agent", risk_agent)
    builder.add_node("decision_orchestrator", orchestrator_agent)
    builder.add_node("route_optimizer", route_agent)
    builder.add_node("notification_agent", notification_agent)
    builder.add_node("cold_storage_agent", cold_storage_agent)
    builder.add_node("insurance_agent", insurance_agent)
    builder.add_node("compliance_agent", compliance_agent)

    # Sequential detection pipeline
    builder.add_edge(START, "monitor_agent")
    builder.add_edge("monitor_agent", "anomaly_agent")
    builder.add_edge("anomaly_agent", "risk_agent")

    # Conditional routing after risk assessment
    builder.add_conditional_edges("risk_agent", should_escalate, {
        "awaiting_hitl": "decision_orchestrator",   # HITL gate via interrupt_before
        "decision_orchestrator": "decision_orchestrator",
        "compliance_agent": "compliance_agent",
    })

    # Fan-out from orchestrator using Send API
    builder.add_conditional_edges("decision_orchestrator", route_orchestrator)

    # All action agents converge to END
    for node in ["route_optimizer", "notification_agent",
                 "cold_storage_agent", "insurance_agent", "compliance_agent"]:
        builder.add_edge(node, END)

    conn = sqlite3.connect(db_path, check_same_thread=False)
    checkpointer = SqliteSaver(conn)

    return builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["decision_orchestrator"]  # HITL gate
    )
```

---

## 3. Agent Implementations

### 3.1 Monitor Agent

```python
# src/agents/monitor.py

THRESHOLDS = {
    "vaccine":    {"temp_min": 2.0, "temp_max": 8.0, "humidity_max": 75.0, "shock_max": 2.0},
    "biologics":  {"temp_min": -20.0, "temp_max": -15.0, "humidity_max": 60.0, "shock_max": 1.5},
    "default":    {"temp_min": 2.0, "temp_max": 25.0, "humidity_max": 80.0, "shock_max": 3.0},
}

def monitor_agent(state: CargoState) -> dict:
    reading = state["latest_reading"]
    cargo_type = state["cargo_type"].lower()
    thresholds = THRESHOLDS.get(cargo_type, THRESHOLDS["default"])

    breaches = []
    if not (thresholds["temp_min"] <= reading.temperature_c <= thresholds["temp_max"]):
        breaches.append(f"Temperature {reading.temperature_c}°C outside range "
                       f"[{thresholds['temp_min']}, {thresholds['temp_max']}]")
    if reading.humidity_pct > thresholds["humidity_max"]:
        breaches.append(f"Humidity {reading.humidity_pct}% exceeds {thresholds['humidity_max']}%")
    if reading.shock_g > thresholds["shock_max"]:
        breaches.append(f"Shock {reading.shock_g}g exceeds {thresholds['shock_max']}g")
    if reading.customs_status == "held":
        breaches.append("Shipment held at customs")

    return {
        "telemetry_window": [reading],
        "audit_log": [AuditEntry(
            entry_id=str(uuid4()),
            timestamp=datetime.utcnow(),
            agent_name="monitor_agent",
            action_type="THRESHOLD_CHECK",
            action_detail=f"Breaches: {breaches}" if breaches else "All clear",
            reasoning="Threshold comparison against GDP cold-chain guidelines",
            severity="LOW" if not breaches else "MEDIUM",
            gdp_compliant=True,
            shipment_id=state["shipment_id"]
        )]
    }
```

### 3.2 Anomaly Detection Agent

```python
# src/agents/anomaly_detector.py

import numpy as np
from anthropic import Anthropic

client = Anthropic()

def anomaly_agent(state: CargoState) -> dict:
    window = state["telemetry_window"][-20:]  # last 20 readings
    temps = [r.temperature_c for r in window]
    
    # Statistical detection
    mean, std = np.mean(temps), np.std(temps)
    z_score = abs((state["latest_reading"].temperature_c - mean) / std) if std > 0 else 0
    
    anomalies = []
    if z_score > 3.0:
        # LLM contextual analysis
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            messages=[{
                "role": "user",
                "content": f"""Analyze this temperature anomaly for pharmaceutical cargo:
                
Cargo: {state['cargo_type']} ({state['cargo_description']})
Current temp: {state['latest_reading'].temperature_c}°C
Recent temps (last 20 readings): {temps}
Z-score: {z_score:.2f}
Customs status: {state['latest_reading'].customs_status}
Location: {state['latest_reading'].latitude}, {state['latest_reading'].longitude}

Classify severity (LOW/MEDIUM/HIGH/CRITICAL) and explain in 2 sentences why.
Return JSON: {{"severity": "...", "description": "...", "anomaly_type": "..."}}"""
            }]
        )
        
        result = json.loads(response.content[0].text)
        anomalies.append(AnomalyRecord(
            anomaly_id=str(uuid4()),
            shipment_id=state["shipment_id"],
            timestamp=datetime.utcnow(),
            anomaly_type=result["anomaly_type"],
            severity=result["severity"],
            z_score=z_score,
            description=result["description"],
            raw_value=state["latest_reading"].temperature_c,
            threshold_value=8.0
        ))

    return {"anomalies": anomalies}
```

### 3.3 Risk Assessment Agent

```python
# src/agents/risk_assessor.py

RISK_TOOLS = [
    {
        "name": "calculate_spoilage_probability",
        "description": "Estimates vaccine spoilage probability given temperature excursion",
        "input_schema": {
            "type": "object",
            "properties": {
                "cargo_type": {"type": "string"},
                "temp_excursion_c": {"type": "number", "description": "Degrees above max safe temp"},
                "duration_minutes": {"type": "number"}
            },
            "required": ["cargo_type", "temp_excursion_c", "duration_minutes"]
        }
    },
    {
        "name": "get_route_eta",
        "description": "Returns remaining time to destination in minutes",
        "input_schema": {
            "type": "object",
            "properties": {"shipment_id": {"type": "string"}},
            "required": ["shipment_id"]
        }
    }
]

def risk_agent(state: CargoState) -> dict:
    if not state["anomalies"]:
        return {"spoilage_probability": 0.0, "delay_risk": 0.0, "severity": "LOW"}

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        tools=RISK_TOOLS,
        messages=[{
            "role": "user",
            "content": f"""Assess the risk for this pharmaceutical shipment:

Shipment: {state['shipment_id']} ({state['cargo_type']})
Route: {state['origin_city']} → {state['destination_city']}
Anomalies detected: {[a.model_dump() for a in state['anomalies']]}
Latest reading: {state['latest_reading'].model_dump()}

Use the available tools to calculate spoilage probability and route ETA.
Then determine overall risk severity (LOW/MEDIUM/HIGH/CRITICAL).
Return your final assessment as JSON:
{{"spoilage_probability": 0.0-1.0, "delay_risk": 0.0-1.0, "severity": "...", "reasoning": "..."}}"""
        }]
    )

    # Handle tool calls (agentic loop)
    tool_results = _execute_tool_calls(response, state)
    final = _parse_final_assessment(response, tool_results)
    
    return {
        "spoilage_probability": final["spoilage_probability"],
        "delay_risk": final["delay_risk"],
        "severity": final["severity"],
        "audit_log": [_make_audit_entry("risk_agent", final["reasoning"], state)]
    }
```

### 3.4 Decision Orchestrator Agent

```python
# src/agents/orchestrator.py

ACTION_TOOLS = [
    {"name": "recommend_reroute", "description": "Flag for route optimization"},
    {"name": "recommend_cold_storage", "description": "Flag for emergency cold storage"},
    {"name": "recommend_customs_escalation", "description": "Flag for customs priority escalation"},
    {"name": "recommend_hospital_notification", "description": "Flag to notify downstream hospitals"},
    {"name": "recommend_insurance_claim", "description": "Flag to initiate insurance claim"},
]

def orchestrator_agent(state: CargoState) -> dict:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        tools=ACTION_TOOLS,
        system="""You are the Decision Orchestrator for a pharmaceutical cold-chain monitoring system.
You must balance: (1) cargo integrity/spoilage risk, (2) intervention cost, 
(3) regulatory obligations (GDP/FDA — if threshold breached, notification is mandatory),
(4) downstream patient impact. Use tools to flag required actions.""",
        messages=[{
            "role": "user",
            "content": f"""Determine required interventions for this incident:

Shipment: {state['shipment_id']} — {state['cargo_type']}
Route: {state['origin_city']} → {state['destination_city']}
Spoilage probability: {state['spoilage_probability']:.0%}
Delay risk: {state['delay_risk']:.0%}
Severity: {state['severity']}
Anomalies: {[a.description for a in state['anomalies']]}

Call ALL relevant action tools. Do not skip mandatory regulatory actions."""
        }]
    )

    actions = _extract_tool_calls(response)
    return {
        "recommended_actions": actions,
        "orchestrator_reasoning": _extract_reasoning(response),
        "audit_log": [_make_audit_entry("decision_orchestrator", 
                                         _extract_reasoning(response), state)]
    }
```

---

## 4. Telemetry Simulator

```python
# src/simulator/telemetry.py

import numpy as np
from datetime import datetime, timedelta

class TelemetrySimulator:
    """Generates realistic synthetic cold-chain telemetry."""
    
    BASELINES = {
        "vaccine": {"temp": 4.5, "humidity": 55.0, "shock": 0.3},
        "biologics": {"temp": -18.0, "humidity": 40.0, "shock": 0.2},
    }

    def __init__(self, cargo_type: str, shipment_id: str):
        self.cargo_type = cargo_type
        self.shipment_id = shipment_id
        self.baseline = self.BASELINES.get(cargo_type, self.BASELINES["vaccine"])
        self._step = 0
        self._anomaly_injected = False

    def next_reading(self, inject_anomaly: str | None = None) -> TelemetryReading:
        self._step += 1
        temp = self.baseline["temp"] + np.random.normal(0, 0.3)
        humidity = self.baseline["humidity"] + np.random.normal(0, 1.5)
        shock = max(0, self.baseline["shock"] + np.random.exponential(0.1))

        if inject_anomaly == "temp_spike":
            temp = self.baseline["temp"] + np.random.uniform(8, 15)  # major excursion
        elif inject_anomaly == "gradual_drift":
            temp = self.baseline["temp"] + (self._step * 0.08)       # slow rise
        elif inject_anomaly == "shock_event":
            shock = np.random.uniform(3.5, 6.0)

        return TelemetryReading(
            shipment_id=self.shipment_id,
            timestamp=datetime.utcnow(),
            temperature_c=round(temp, 2),
            humidity_pct=round(np.clip(humidity, 0, 100), 1),
            shock_g=round(shock, 3),
            latitude=self._interpolate_lat(),
            longitude=self._interpolate_lon(),
            altitude_m=float(np.random.choice([0, 500, 10000, 35000])),
            customs_status=self._customs_status(),
            carrier_id="CARRIER_DHL_001"
        )

    def _customs_status(self) -> str:
        if self._step in range(15, 20):  # simulate customs hold
            return "held"
        return "in_transit"

    def _interpolate_lat(self) -> float:
        # Linear interpolation NYC → Frankfurt → Nairobi
        progress = self._step / 100
        waypoints = [40.7128, 50.1109, -1.2921]
        idx = min(int(progress * len(waypoints)), len(waypoints) - 2)
        t = (progress * len(waypoints)) - idx
        return waypoints[idx] + t * (waypoints[idx + 1] - waypoints[idx])

    def _interpolate_lon(self) -> float:
        progress = self._step / 100
        waypoints = [-74.0060, 8.6821, 36.8219]
        idx = min(int(progress * len(waypoints)), len(waypoints) - 2)
        t = (progress * len(waypoints)) - idx
        return waypoints[idx] + t * (waypoints[idx + 1] - waypoints[idx])
```

---

## 5. FastAPI Endpoints

```python
# src/api/main.py

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI(title="AI Cargo Monitor API")
graph = build_graph()

@app.post("/api/ingest/{shipment_id}")
async def ingest_telemetry(shipment_id: str, reading: TelemetryReading):
    """Receive telemetry reading and trigger agent pipeline."""
    config = {"configurable": {"thread_id": shipment_id}}
    state_update = {"latest_reading": reading, "telemetry_window": [reading]}
    result = await graph.ainvoke(state_update, config=config)
    return {"status": "processed", "severity": result["severity"]}

@app.get("/api/status/{shipment_id}")
async def get_status(shipment_id: str):
    """Get current state of a shipment's monitoring."""
    config = {"configurable": {"thread_id": shipment_id}}
    state = graph.get_state(config)
    return state.values

@app.post("/api/approve/{shipment_id}")
async def approve_action(shipment_id: str, decision: HumanDecision):
    """Submit human approval/rejection for a pending HITL decision."""
    config = {"configurable": {"thread_id": shipment_id}}
    graph.update_state(config, {
        "human_decision": decision.decision,
        "human_notes": decision.notes,
        "awaiting_human_approval": False
    })
    await graph.ainvoke(None, config=config)  # resume graph
    return {"status": "resumed"}

@app.get("/api/audit/{shipment_id}")
async def get_audit_log(shipment_id: str):
    """Retrieve full audit trail for a shipment."""
    config = {"configurable": {"thread_id": shipment_id}}
    state = graph.get_state(config)
    return {"audit_log": state.values.get("audit_log", [])}

@app.get("/api/stream/{shipment_id}")
async def stream_events(shipment_id: str):
    """SSE stream of real-time agent events for dashboard."""
    config = {"configurable": {"thread_id": shipment_id}}
    async def event_generator():
        async for event in graph.astream_events(None, config=config, version="v2"):
            yield f"data: {json.dumps(event)}\n\n"
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

---

## 6. Streamlit Dashboard

```python
# src/dashboard/app.py  (key sections)

import streamlit as st
import plotly.graph_objects as go
import requests

st.set_page_config(page_title="AI Cargo Monitor", layout="wide", page_icon="🌡️")

# Layout
col_map, col_metrics = st.columns([2, 1])
col_chart, col_log = st.columns([3, 2])

with col_map:
    st.subheader("Live Shipment Map")
    # Plotly map showing route + current position
    fig_map = go.Figure(go.Scattermapbox(...))
    st.plotly_chart(fig_map, use_container_width=True)

with col_metrics:
    state = requests.get(f"/api/status/{shipment_id}").json()
    severity = state["severity"]
    color = {"LOW":"🟢","MEDIUM":"🟡","HIGH":"🟠","CRITICAL":"🔴"}[severity]
    st.metric("Severity", f"{color} {severity}")
    st.metric("Spoilage Risk", f"{state['spoilage_probability']:.0%}")
    st.metric("Delay Risk", f"{state['delay_risk']:.0%}")
    st.metric("Temperature", f"{state['latest_reading']['temperature_c']}°C")

with col_chart:
    # Rolling temperature chart
    temps = [r["temperature_c"] for r in state["telemetry_window"]]
    fig = go.Figure()
    fig.add_trace(go.Scatter(y=temps, name="Temperature", line=dict(color="#ef4444")))
    fig.add_hline(y=8.0, line_dash="dash", line_color="#f59e0b", annotation_text="Max safe")
    fig.add_hline(y=2.0, line_dash="dash", line_color="#3b82f6", annotation_text="Min safe")
    st.plotly_chart(fig, use_container_width=True)

# HITL Modal
if state.get("awaiting_human_approval"):
    with st.container():
        st.error("⚠️ Human approval required")
        st.write(state["orchestrator_reasoning"])
        st.write(f"Recommended actions: {state['recommended_actions']}")
        col_approve, col_reject = st.columns(2)
        if col_approve.button("✅ Approve", type="primary"):
            requests.post(f"/api/approve/{shipment_id}", 
                         json={"decision": "approved", "notes": ""})
            st.rerun()
        if col_reject.button("❌ Reject"):
            requests.post(f"/api/approve/{shipment_id}",
                         json={"decision": "rejected", "notes": "Manual override"})
            st.rerun()

# Auto-refresh
st.rerun()
```

---

## 7. Compliance & Audit Log Schema

Every agent action produces an `AuditEntry`. The format follows FDA 21 CFR Part 11:

```json
{
  "entry_id": "uuid",
  "timestamp": "2026-04-16T14:23:01Z",
  "agent_name": "decision_orchestrator",
  "action_type": "INTERVENTION_RECOMMENDED",
  "action_detail": "REROUTE + NOTIFY_HOSPITALS triggered",
  "reasoning": "Spoilage probability 0.78 with 4.2h remaining route time. Regulatory obligation under GDP Article 9.2 requires hospital notification when cold-chain breach exceeds 30 minutes.",
  "severity": "CRITICAL",
  "gdp_compliant": true,
  "shipment_id": "SHP-2026-0042"
}
```

---

## 8. Environment Variables

```bash
# .env.example
ANTHROPIC_API_KEY=sk-ant-...
DATABASE_URL=sqlite:///cargo.db
TELEMETRY_POLL_INTERVAL=30       # seconds
HITL_TIMEOUT_MINUTES=15
MAX_TELEMETRY_WINDOW=50          # readings to keep in state
LOG_LEVEL=INFO
DASHBOARD_PORT=8501
API_PORT=8000
```

---

## 9. Key Dependencies

```txt
# requirements.txt
anthropic>=0.40.0
langgraph>=0.2.0
langchain-anthropic>=0.3.0
fastapi>=0.115.0
uvicorn>=0.32.0
streamlit>=1.40.0
plotly>=5.24.0
pydantic>=2.9.0
numpy>=2.1.0
python-dotenv>=1.0.0
httpx>=0.27.0
pytest>=8.3.0
pytest-asyncio>=0.24.0
```
