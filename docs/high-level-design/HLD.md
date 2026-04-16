# High Level Design (HLD) — AI Cargo Monitor
**UMD Agentic AI Hackathon 2026 · Case 6**

---

## 1. Problem Statement

A global pharmaceutical distributor ships temperature-sensitive vaccines across multiple countries in sensor-equipped smart containers. When something goes wrong mid-shipment — temperature spike, route delay, customs hold, equipment failure — the current manual process is too slow. By the time a human notices, vaccines may be spoiled and hospitals are left without stock for scheduled patient appointments.

**Goal:** Build an autonomous multi-agent AI system that detects risks early, reasons about the best intervention, executes a cascade of corrective actions, and maintains a full audit trail — all while keeping a human in the loop for high-stakes decisions.

---

## 2. System Goals

| Goal | Description |
|------|-------------|
| **Real-time monitoring** | Ingest telemetry every 30 seconds; detect anomalies within 1 cycle |
| **Autonomous action** | Execute low-severity interventions without human approval |
| **Human-in-the-loop** | Gate HIGH/CRITICAL decisions behind human approval |
| **Cascading coordination** | One risk event triggers up to 5 parallel downstream actions |
| **Audit trail** | Every decision logged with reasoning, timestamp, agent ID |
| **Regulatory compliance** | GDP/FDA-aligned thresholds and documentation |
| **Demo-ready** | Live dashboard shows the full system working end-to-end |

---

## 3. High-Level Components

```
┌──────────────────────────────────────────────────────────────────┐
│                        AI CARGO MONITOR                          │
│                                                                  │
│  ┌─────────────┐    ┌──────────────────────────────────────┐    │
│  │  Telemetry  │───►│         LangGraph Agent Pipeline      │    │
│  │  Simulator  │    │                                      │    │
│  └─────────────┘    │  Monitor → Anomaly → Risk →          │    │
│                     │  Orchestrator → [Actions]            │    │
│  ┌─────────────┐    │                                      │    │
│  │  External   │───►│  Human-in-the-Loop Gate              │    │
│  │  Data Feeds │    └───────────────┬──────────────────────┘    │
│  └─────────────┘                   │                            │
│                                    ▼                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              FastAPI Backend                            │   │
│  │   /ingest · /status · /approve · /history              │   │
│  └────────────────────────┬────────────────────────────────┘   │
│                           │                                     │
│  ┌────────────────────────▼────────────────────────────────┐   │
│  │           Streamlit Dashboard                           │   │
│  │  Live map · Telemetry charts · Risk gauge ·             │   │
│  │  Alert feed · HITL approval modal · Audit log           │   │
│  └─────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

---

## 4. Agent Responsibilities

### 4.1 Monitor Agent
- **Input:** Raw telemetry stream (temp, humidity, shock, GPS, customs status)
- **Output:** Processed readings with breach flags
- **Logic:** Compares each reading against configured thresholds (GDP cold-chain: 2–8°C for vaccines)
- **Triggers:** Passes to Anomaly Agent on any breach or sustained deviation

### 4.2 Anomaly Detection Agent
- **Input:** Processed readings + historical window
- **Output:** Classified anomaly records with severity
- **Logic:** 
  - Statistical: Z-score > 3.0, IQR-based outlier detection
  - LLM-based: Claude analyzes pattern context ("sudden spike vs. gradual drift")
- **Output severity:** LOW · MEDIUM · HIGH · CRITICAL

### 4.3 Risk Assessment Agent
- **Input:** Anomaly records + external context (flight delay, weather, customs)
- **Output:** Spoilage probability (0–1), delay risk (0–1), composite severity
- **Logic:** Claude claude-sonnet-4-6 with structured tool use:
  - Tool: `get_spoilage_model(cargo_type, temp_excursion_duration)`
  - Tool: `get_remaining_route_time(shipment_id)`
  - Tool: `get_customs_status(location)`
- **Key insight:** Combines sensor data + external logistics data for holistic risk scoring

### 4.4 Decision Orchestrator Agent
- **Input:** Risk scores + full cargo context
- **Output:** Ordered list of recommended actions with reasoning
- **Logic:** Claude claude-sonnet-4-6 reasons over:
  - Spoilage probability vs. intervention cost
  - Regulatory obligation (must notify if GDP threshold breached)
  - Time remaining in route vs. spoilage timeline
- **Routing:** Uses LangGraph `conditional_edges` to fan out to action agents

### 4.5 Route Optimizer Agent
- **Input:** Current route, delay/risk data
- **Output:** Alternative route options ranked by cost, time, risk
- **Logic:** Calls simulated routing API, Claude selects optimal option

### 4.6 Notification Agent
- **Input:** Severity + impacted facilities list
- **Output:** Alerts sent, appointments rescheduled
- **Logic:** Generates context-aware messages per recipient type (hospital, clinic, distributor)

### 4.7 Cold Storage Agent
- **Input:** Current location, temperature breach severity
- **Output:** Nearest available cold storage facility booked
- **Logic:** Queries simulated facility database, books emergency storage

### 4.8 Insurance Claim Agent
- **Input:** Anomaly record + audit trail
- **Output:** Insurance claim ID, supporting evidence package
- **Logic:** Auto-generates claim documentation with sensor data, timeline, agent reasoning

### 4.9 Compliance Agent
- **Input:** All agent actions + decisions
- **Output:** GDP/FDA-compliant audit log entries
- **Logic:** Formats every event per 21 CFR Part 11 structure, immutably writes to SQLite

---

## 5. Key Design Decisions

### 5.1 Why LangGraph?
LangGraph provides:
- **Stateful execution** — the full `CargoState` persists across all agent nodes
- **Checkpointing** — if the system crashes mid-incident, state is recoverable
- **`interrupt_before`** — native HITL without custom implementation
- **Streaming** — `graph.astream()` enables real-time dashboard updates
- **Visualization** — the agent graph can be rendered visually for the demo

### 5.2 Why Claude claude-sonnet-4-6?
- Best reasoning for multi-variable trade-off decisions (cost vs. risk vs. regulation)
- Structured tool use for calling simulated external APIs
- Generates human-readable reasoning chains for the audit log
- Excellent performance at generating synthetic data

### 5.3 Why Streamlit for dashboard?
- Pure Python — no context switch to JS/React
- Built-in support for real-time updates (`st.rerun()`)
- Plotly integration for rich telemetry visualizations
- Fast to build, looks good in demo video

### 5.4 Synthetic Data Approach
All data is generated programmatically:
- **Normal operation:** Numpy-based Gaussian noise around valid baselines
- **Failure scenarios:** Scripted injection at defined time offsets
- **External feeds:** Mocked REST endpoints that return pre-seeded JSON
- **Hospital data:** LLM-generated appointment schedules

---

## 6. Failure Scenarios (Demo Scripts)

| Scenario | Trigger | Expected Agent Response |
|----------|---------|------------------------|
| `temp_spike` | Refrigeration failure at 2h into flight | Anomaly detected → HIGH risk → HITL → Reroute + Cold storage |
| `customs_hold` | Hold at Frankfurt for 4+ hours | Delay risk HIGH → Notify hospitals → Reschedule appointments |
| `compound_failure` | Temp spike + route delay simultaneously | CRITICAL → All 5 action agents triggered |
| `gradual_drift` | Temperature slowly rising over 3h | MEDIUM → Monitor closely, notify distributor |
| `false_alarm` | Brief spike, recovers immediately | LOW → Log only, no escalation |

---

## 7. Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| Telemetry ingestion latency | < 2 seconds end-to-end |
| Agent pipeline execution | < 30 seconds for CRITICAL scenario |
| Dashboard refresh rate | Every 5 seconds |
| Audit log write | Synchronous, before action execution |
| HITL response window | 15-minute auto-escalation |
| Uptime (demo) | Single-machine, no external dependencies |

---

## 8. Out of Scope

- Real IoT device integration (replaced by simulator)
- Production-grade authentication/authorization
- Real insurance API integration
- Multi-tenant support
- Mobile app

---

## 9. Project Folder Structure

```
ai-cargo-monitor/
├── src/
│   ├── agents/              # One file per agent
│   │   ├── monitor.py
│   │   ├── anomaly_detector.py
│   │   ├── risk_assessor.py
│   │   ├── orchestrator.py
│   │   ├── route_optimizer.py
│   │   ├── notification.py
│   │   ├── cold_storage.py
│   │   ├── insurance.py
│   │   └── compliance.py
│   ├── graph/
│   │   ├── cargo_graph.py   # LangGraph graph definition
│   │   └── state.py         # CargoState TypedDict
│   ├── simulator/
│   │   ├── telemetry.py     # Synthetic telemetry generator
│   │   └── scenarios.py     # Failure scenario scripts
│   ├── api/
│   │   └── main.py          # FastAPI app
│   ├── dashboard/
│   │   └── app.py           # Streamlit dashboard
│   └── tools/               # LangGraph tool definitions
│       ├── spoilage_model.py
│       ├── routing.py
│       ├── notifications.py
│       └── compliance_rules.py
├── data/
│   └── synthetic/           # Pre-generated scenario data
├── tests/
│   ├── test_agents.py
│   ├── test_graph.py
│   └── test_simulator.py
├── docs/                    # This folder
├── docker-compose.yml
├── requirements.txt
└── .env.example
```
