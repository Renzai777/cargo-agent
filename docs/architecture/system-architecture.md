# System Architecture — AI Cargo Monitor
**UMD Agentic AI Hackathon 2026 · Case 6**
**Stack:** Python 3.11 · LangGraph · Claude claude-sonnet-4-6 · FastAPI · Streamlit

---

## Overview

The AI Cargo Monitor is a multi-agent system built on LangGraph that continuously monitors pharmaceutical cold-chain shipments in real time. When a risk is detected (temperature excursion, route delay, customs hold, equipment failure), the system autonomously reasons over the situation, determines the optimal intervention, and executes a cascade of coordinated actions — all while maintaining a human-in-the-loop approval gate for high-stakes decisions.

---

## Architectural Layers

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1: DATA SOURCES                                       │
│  Telemetry Simulator · Flight APIs · Customs Feed ·          │
│  Hospital Schedule DB · GDP/FDA Rules Engine                 │
├─────────────────────────────────────────────────────────────┤
│  LAYER 2: DETECTION PIPELINE (LangGraph Sequential Nodes)   │
│  Monitor Agent → Anomaly Agent → Risk Assessment Agent       │
│                           ↕                                  │
│                  Human-in-the-Loop Gate                      │
│                  (interrupt_before on HIGH/CRITICAL)         │
├─────────────────────────────────────────────────────────────┤
│  LAYER 3: DECISION ENGINE                                    │
│  Decision Orchestrator Agent (Claude claude-sonnet-4-6 + tools)   │
│  conditional_edges fan-out to action agents                  │
├─────────────────────────────────────────────────────────────┤
│  LAYER 4: ACTION AGENTS (parallel execution)                │
│  Route Optimizer · Notification · Cold Storage ·             │
│  Insurance Claim · Compliance Logger                         │
├─────────────────────────────────────────────────────────────┤
│  LAYER 5: OUTPUT / PERSISTENCE                               │
│  Streamlit Dashboard · FastAPI REST · SQLite · Plotly        │
└─────────────────────────────────────────────────────────────┘
```

---

## Agent Topology

### Sequential Detection Pipeline
```
START
  │
  ▼
[Monitor Agent]──── polls telemetry every N seconds
  │                 detects threshold breaches (temp, humidity, shock)
  ▼
[Anomaly Agent]──── statistical analysis (Z-score, IQR)
  │                 + LLM-based pattern reasoning
  ▼
[Risk Agent]──────── computes spoilage probability (0–1)
  │                  computes delay risk score (0–1)
  │                  classifies severity: LOW / MEDIUM / HIGH / CRITICAL
  │
  ├── severity < HIGH ──► [Compliance Logger] ──► END
  │
  └── severity >= HIGH ─► [HITL Gate] ──► wait for human approval
                              │
                              ▼ (approved)
                    [Decision Orchestrator]
```

### Decision Orchestrator Fan-Out
```
[Decision Orchestrator]
  │
  ├── REROUTE ────────────► [Route Optimizer Agent]
  ├── COLD_STORAGE ────────► [Cold Storage Agent]
  ├── CUSTOMS_ESCALATE ────► [Compliance Agent]
  ├── NOTIFY_HOSPITALS ────► [Notification Agent]
  ├── FILE_INSURANCE ──────► [Insurance Claim Agent]
  └── LOG_ONLY ────────────► [Compliance Agent]
  
  (Multiple branches can activate simultaneously via Send/parallel nodes)
```

---

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Agent Framework | LangGraph 0.2+ | Stateful multi-agent graph execution |
| LLM | Claude claude-sonnet-4-6 (claude-sonnet-4-6) | Reasoning within each agent |
| LLM SDK | Anthropic Python SDK | Claude API calls with tool use |
| API Layer | FastAPI | REST endpoints, webhook ingestion |
| Dashboard | Streamlit | Real-time demo UI |
| Visualization | Plotly | Telemetry charts, risk gauges, maps |
| State Store | SQLite + LangGraph checkpointer | Persistent agent state, audit trail |
| Data Models | Pydantic v2 | Type-safe schemas throughout |
| Data Simulation | Python + Claude | Synthetic telemetry generation |
| Testing | pytest | Unit + integration tests |

---

## LangGraph State Schema

```python
class CargoState(TypedDict):
    # Shipment identity
    shipment_id: str
    cargo_type: str                    # e.g. "COVID-19 Vaccine"
    origin: str
    destination: str
    
    # Live telemetry
    telemetry: list[TelemetryReading]  # sliding window, last N readings
    latest_reading: TelemetryReading
    
    # Detection outputs
    anomalies: list[AnomalyRecord]
    risk_score: float                  # 0.0 – 1.0
    severity: Literal["LOW","MEDIUM","HIGH","CRITICAL"]
    
    # Decision outputs
    recommended_actions: list[str]
    orchestrator_reasoning: str        # LLM chain-of-thought
    
    # Action outputs
    route_recommendation: RouteOption | None
    notifications_sent: list[str]
    cold_storage_booked: bool
    insurance_claim_id: str | None
    
    # Compliance
    audit_log: list[AuditEntry]
    gdp_compliant: bool
    
    # HITL
    awaiting_human_approval: bool
    human_decision: Literal["approved","rejected","modified"] | None
```

---

## Data Flow

```
Telemetry Simulator
      │  (JSON stream: {temp, humidity, shock, lat, lon, timestamp})
      ▼
FastAPI /ingest endpoint
      │  (validates schema, writes to SQLite)
      ▼
LangGraph Graph.astream()
      │  (streams state updates to Streamlit dashboard via SSE)
      ▼
Agent Pipeline executes
      │  (each node reads/writes CargoState)
      ▼
SQLite Audit Log
      │  (every agent action appended, immutable)
      ▼
Streamlit Dashboard re-renders
      (real-time: telemetry chart, risk gauge, action log, HITL modal)
```

---

## Human-in-the-Loop Design

LangGraph's `interrupt_before` mechanism is used for any action with severity >= HIGH:

```python
graph.add_node("decision_orchestrator", orchestrator_node)
graph.add_node("route_optimizer", route_node)

# Interrupt BEFORE executing route_optimizer if severity is HIGH/CRITICAL
graph = graph.compile(
    checkpointer=SqliteSaver(conn),
    interrupt_before=["route_optimizer", "notification_agent", "insurance_agent"]
)
```

The Streamlit dashboard presents the pending decision with:
- Full reasoning chain from Decision Orchestrator
- Recommended action + confidence score
- One-click Approve / Modify / Reject buttons
- 15-minute auto-escalation timer

---

## Synthetic Data Strategy

Since no real dataset is provided, all data is synthetically generated:

| Data Type | Generation Method |
|-----------|------------------|
| Normal telemetry | Python numpy — Gaussian noise around baseline |
| Temperature excursion | Scripted anomaly injection at random intervals |
| Route delays | Simulated weather/congestion events |
| Customs holds | Random hold probability per country |
| Hospital schedules | LLM-generated appointment data |
| FDA compliance thresholds | Based on real WHO/GDP guidelines (public) |

Scenario scripts inject realistic failure modes:
- `scenario_temp_spike.py` — refrigeration unit failure mid-flight
- `scenario_customs_hold.py` — unexpected hold at Frankfurt customs
- `scenario_multi_failure.py` — compound failure (temp + delay)

---

## Deployment (Demo)

```
Local machine:
  ├── python src/simulator/run.py     # streams synthetic telemetry
  ├── uvicorn src/api.main:app        # FastAPI ingest + REST
  ├── streamlit run src/dashboard/app.py   # live dashboard
  └── (LangGraph runs embedded in FastAPI worker)
```

All components run locally. No cloud required for demo. One `docker-compose up` starts everything.

---

## Security & Compliance Notes

- All agent decisions are immutably logged to SQLite with timestamps
- GDP thresholds sourced from public WHO cold-chain guidelines
- FDA 21 CFR Part 11 audit trail format applied to compliance logs
- No real PII or patient data — all synthetic
