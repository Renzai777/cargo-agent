# AI Cargo Monitor — Pharmaceutical Cold-Chain Intelligence

> **UMD Agentic AI Hackathon 2026 · Case 6**  
> A production-grade, multi-agent AI system that monitors pharmaceutical cold-chain shipments in real time, detects anomalies, predicts failures before they happen, and autonomously executes coordinated interventions — with a human-in-the-loop approval gate for high-stakes decisions.

---

## What This System Does

When a shipment of COVID-19 vaccines leaves New York bound for Nairobi, dozens of things can go wrong: a refrigeration unit fails mid-flight, humidity spikes above safe levels, customs holds the cargo in Frankfurt for 48 hours, or a shock sensor registers a hard landing. Any one of these events can ruin millions of dollars of life-saving medicine.

This system watches every sensor reading, reasons about risk using Claude AI, predicts temperature breaches before they happen, and automatically coordinates responses: rerouting cargo, booking emergency cold storage, notifying destination hospitals, and filing insurance claims — all in seconds, not hours.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│  LAYER 1: TELEMETRY INGESTION                                    │
│  Simulator · FastAPI /ingest endpoint · Pydantic validation      │
├──────────────────────────────────────────────────────────────────┤
│  LAYER 2: DETECTION PIPELINE  (LangGraph sequential nodes)       │
│  Monitor Agent → Predictor Agent → Anomaly Agent → Risk Agent    │
├──────────────────────────────────────────────────────────────────┤
│  LAYER 3: DECISION ENGINE                                        │
│  Decision Orchestrator  (Claude + Extended Thinking)             │
│  Conditional fan-out via LangGraph Send()                        │
├──────────────────────────────────────────────────────────────────┤
│  LAYER 4: ACTION AGENTS  (parallel execution)                    │
│  Route Optimizer · Notification · Cold Storage ·                 │
│  Insurance · Inventory · Compliance                              │
├──────────────────────────────────────────────────────────────────┤
│  LAYER 5: PRESENTATION                                           │
│  FastAPI REST API · Streamlit Dashboard · Plotly charts          │
└──────────────────────────────────────────────────────────────────┘
```

---

## Agent Pipeline — Step by Step

```
START
  │
  ▼
[Monitor Agent]
  │  Reads latest telemetry reading
  │  Checks GDP/WHO thresholds: temperature, humidity, shock, customs
  │  Emits AnomalyRecord for each breach
  ▼
[Predictor Agent]
  │  Runs linear regression (numpy polyfit) on the telemetry window
  │  Forecasts the next 20 readings (10 minutes ahead)
  │  Reports: "Temperature will breach 8°C threshold in 6 minutes"
  ▼
[Anomaly Detector]
  │  Computes Z-score for the latest reading vs rolling window
  │  If Z-score > 3.0: calls Claude AI to classify severity + context
  │  Claude API feature used: prompt caching (system prompt cached)
  ▼
[Risk Assessor]
  │  Claude AI with tool use:
  │    • calculate_spoilage_probability(cargo_type, temp_excursion, duration)
  │    • get_route_eta(shipment_id)
  │  Returns: spoilage_probability (0–1), delay_risk (0–1), severity
  │  Claude API feature used: tool use / function calling
  │
  ├── severity LOW/MEDIUM ──────────────────────► [Compliance Agent] → END
  │
  └── severity HIGH/CRITICAL ─► [Decision Orchestrator]
                                    │
                                    │  Claude AI with Extended Thinking:
                                    │  deliberates over cost-benefit trade-offs
                                    │  before selecting interventions
                                    │
                                    │  Claude API features used:
                                    │    • Extended thinking (budget_tokens=10000)
                                    │    • Prompt caching
                                    │
                                    ▼  (parallel fan-out via LangGraph Send)
                    ┌──────────────────────────────────────────┐
                    │              │           │               │
                    ▼              ▼           ▼               ▼
             [Route         [Notification  [Cold Storage  [Insurance
             Optimizer]      Agent]        Agent]         Agent]
                    │              │           │               │
                    └──────────────┴───────────┴───────────────┘
                                    │
                                    ▼
                            [Compliance Agent]
                                    │
                                   END
```

---

## Claude AI — How and Where It's Used

This project uses Claude through the [Anthropic Python SDK](https://github.com/anthropic-sdk/anthropic-python). Three distinct Claude API capabilities are demonstrated:

### 1. Tool Use — Risk Assessor Agent (`src/agents/risk_assessor.py`)

The risk assessor gives Claude two domain tools and lets it call them autonomously in an agentic loop:

```python
RISK_TOOLS = [
    {
        "name": "calculate_spoilage_probability",
        "description": "Estimates vaccine/biologics spoilage probability given temperature excursion details",
        "input_schema": { ... }
    },
    {
        "name": "get_route_eta",
        "description": "Returns remaining route time in minutes for a given shipment",
        "input_schema": { ... }
    },
]

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    tools=RISK_TOOLS,
    messages=messages,
)
```

Claude autonomously decides which tools to call, in what order, and synthesises a final JSON risk report: `{"spoilage_probability": 0.78, "delay_risk": 0.45, "severity": "HIGH", "reasoning": "..."}`.

### 2. Extended Thinking — Decision Orchestrator (`src/agents/orchestrator.py`)

For high-stakes intervention decisions, Claude is given a budget of 10,000 thinking tokens to deliberate before acting. This exposes Claude's reasoning chain in the dashboard:

```python
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=16000,
    thinking={"type": "enabled", "budget_tokens": 10000},
    system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
    messages=[{"role": "user", "content": prompt}],
)

thinking_text = next((b.thinking for b in response.content if b.type == "thinking"), "")
response_text = next((b.text for b in response.content if b.type == "text"), "")
```

The `thinking_text` (Claude's internal deliberation) is stored in state and displayed in the Streamlit dashboard as "Claude's Reasoning Chain".

### 3. Prompt Caching — Anomaly Detector & Risk Assessor

Both the anomaly detector and risk assessor mark their system prompts with `cache_control: ephemeral`. Since these agents run on every anomalous reading, caching cuts repeated-call latency and cost significantly:

```python
system=[{
    "type": "text",
    "text": ANOMALY_SYSTEM,
    "cache_control": {"type": "ephemeral"},  # cached across repeated calls
}]
```

### API Key Setup

```bash
# Copy the example env file
cp .env.example .env

# Add your key (get one at https://console.anthropic.com/)
ANTHROPIC_API_KEY=sk-ant-your-key-here
DEMO_MODE=false
```

No API key? Set `DEMO_MODE=true` to run the full pipeline with pre-scripted responses. Every agent still executes; Claude calls are replaced by realistic hardcoded outputs. The Streamlit dashboard, LangGraph graph, and all action agents work identically.

---

## Components In Detail

### `src/graph/state.py` — Shared State Schema

The single source of truth flowing through every agent node. Built with `TypedDict` for LangGraph compatibility and Pydantic models for validation:

| Field | Type | Description |
|---|---|---|
| `telemetry_window` | `list[TelemetryReading]` | Rolling window of sensor readings (append-only) |
| `anomalies` | `list[AnomalyRecord]` | All detected anomalies (append-only) |
| `spoilage_probability` | `float` | 0.0–1.0 risk score from Claude |
| `severity` | `"LOW"\|"MEDIUM"\|"HIGH"\|"CRITICAL"` | Escalation level |
| `recommended_actions` | `list[str]` | Actions chosen by orchestrator |
| `orchestrator_thinking` | `str\|None` | Claude's extended thinking chain |
| `predicted_breach_minutes` | `float\|None` | Minutes until temperature breach |
| `temperature_forecast` | `list[float]` | Next 20 predicted readings |
| `audit_log` | `list[AuditEntry]` | Immutable GDP compliance log |
| `awaiting_human_approval` | `bool` | HITL gate flag |

### `src/graph/cargo_graph.py` — LangGraph Graph

Builds the stateful agent graph with:
- **Sequential detection pipeline**: Monitor → Predictor → Anomaly → Risk
- **Conditional routing**: `_route_after_risk()` dispatches to orchestrator only for HIGH/CRITICAL
- **Parallel fan-out**: `_route_orchestrator()` uses `LangGraph.Send()` to fire action agents in parallel based on which actions the orchestrator selected
- **MemorySaver checkpointer**: Every state transition is persisted, enabling graph resumption after human approval

```python
builder.add_conditional_edges("risk_agent", _route_after_risk, {
    "decision_orchestrator": "decision_orchestrator",
    "compliance_agent":      "compliance_agent",
})
builder.add_conditional_edges("decision_orchestrator", _route_orchestrator)
```

### `src/agents/monitor.py` — Threshold Monitor

Checks every reading against cargo-type-specific GDP/WHO thresholds:

| Cargo Type | Temp Range | Humidity Max | Shock Max |
|---|---|---|---|
| `vaccine` | 2–8°C | 75% | 2.0g |
| `biologics` | −20 to −15°C | 60% | 1.5g |
| `default` | 2–25°C | 80% | 3.0g |

No Claude call here — pure deterministic rule checking for speed and reliability.

### `src/agents/predictor.py` — Predictive Alert Agent

Uses `numpy.polyfit` (degree-1 linear regression) on the telemetry window to extrapolate future temperature readings. If the trend line crosses the safe-temperature threshold within the forecast horizon, it returns `predicted_breach_minutes` so upstream agents can act before the breach occurs.

### `src/agents/anomaly_detector.py` — Statistical + AI Anomaly Classifier

Two-stage process:
1. **Statistical gate**: Computes Z-score vs rolling window. If Z-score < 3.0, skips Claude (no false positive API calls).
2. **Claude classification**: If Z-score ≥ 3.0, asks Claude to classify severity and describe the anomaly in pharmaceutical context. Returns structured JSON: `{"severity": "HIGH", "description": "...", "anomaly_type": "temp_excursion"}`.

### `src/agents/risk_assessor.py` — Agentic Risk Scorer

Claude with tool-use in a multi-turn agentic loop (up to 5 iterations). Claude decides autonomously when to call the spoilage calculator and ETA lookup tools. Returns a final risk report only after both tools have been consulted.

### `src/agents/orchestrator.py` — Decision Orchestrator

The most complex agent. Receives the full incident context, uses Claude with extended thinking to deliberate, and outputs a list of action flags:

| Action Flag | Trigger Condition |
|---|---|
| `REROUTE` | `spoilage_probability > 0.6` |
| `COLD_STORAGE` | `spoilage_probability > 0.6` |
| `NOTIFY_HOSPITALS` | `spoilage_probability > 0.4` or `severity == CRITICAL` |
| `FILE_INSURANCE` | `spoilage_probability > 0.7` |
| `CUSTOMS_ESCALATE` | Customs hold detected |

### `src/agents/route_optimizer.py` — Route Optimizer

Generates 3 alternative route/carrier options with cost, ETA, and risk scores. Activated only when `REROUTE` is in the recommended actions.

### `src/agents/notification.py` — Notification Agent

Sends alerts to destination hospitals about shipment delays. Generates realistic notification messages with shipment ID, estimated impact, and recommended actions.

### `src/agents/cold_storage.py` — Cold Storage Agent

Books emergency refrigerated storage at the nearest airport facility. Returns a booking confirmation with facility name and capacity.

### `src/agents/insurance.py` — Insurance Claim Agent

Initiates an insurance claim for potential product loss. Returns a claim ID and coverage estimate.

### `src/agents/inventory.py` — Inventory Impact Agent

Assesses downstream inventory impact at the destination facility. Calculates how many patient appointments or doses will be affected.

### `src/agents/compliance.py` — Compliance Logger

Always runs (every shipment, every severity level). Writes the final GDP-compliant audit entry with full action trail. Ensures `gdp_compliant: True` in state.

---

### `src/api/main.py` — FastAPI REST Backend

The backend that the Streamlit dashboard (and any external system) communicates with:

| Endpoint | Method | Description |
|---|---|---|
| `/api/shipments/{id}/init` | POST | Initialize a new shipment tracking thread |
| `/api/shipments/{id}/ingest` | POST | Push a telemetry reading into the agent graph |
| `/api/shipments/{id}/status` | GET | Full shipment state snapshot |
| `/api/shipments/{id}/audit` | GET | GDP compliance audit log |
| `/api/shipments/{id}/approve` | POST | Human approval / rejection of pending action |
| `/api/scenarios/{name}/start/{id}` | POST | Start a demo scenario (playback mode) |
| `/api/scenarios/{name}/run/{id}` | POST | Run a complete scenario end-to-end |
| `/api/scenarios` | GET | List available scenarios |
| `/health` | GET | Health check |

Key design decisions:
- **Thread isolation**: Each shipment gets a unique LangGraph thread ID (`shipment_id + uuid4 suffix`) so multiple shipments run independently
- **Async everywhere**: Graph invocations run in an executor to avoid blocking the FastAPI event loop
- **Scenario engine**: Supports both `playback` mode (step-by-step with configurable delay, pauses at HITL gates) and `full` mode (auto-approves, completes instantly)

---

### `src/dashboard/app.py` — Streamlit Demo Frontend

> **This is a demo frontend only.** It is designed to showcase the agent system's capabilities in a compelling visual way. It is not a production UI.

The dashboard provides:

- **Live temperature gauge** — colour-coded (green/amber/red) with the current reading in large font
- **Agent pipeline status** — shows each of the 11 agents as a card: `waiting`, `active`, `done`, or `critical`
- **Temperature forecast chart** — Plotly line chart showing historical readings + predicted future readings from the Predictor Agent
- **Risk gauges** — spoilage probability and delay risk as semi-circular gauges
- **Claude's Reasoning Chain** — the raw extended thinking output from the Decision Orchestrator
- **Action log** — every action the system has taken, timestamped
- **Human-in-the-loop panel** — appears when the graph pauses for approval; shows the full orchestrator reasoning and Approve/Reject/Modify buttons
- **GDP Audit Log** — scrollable table of every agent decision with compliance flag

The dashboard polls the FastAPI `/status` endpoint every 5 seconds and re-renders.

---

### `src/simulator/` — Telemetry Simulator

Generates synthetic IoT sensor data mimicking a real pharmaceutical cold-chain shipment. Four pre-built scenarios:

| Scenario | Description |
|---|---|
| `temp_spike` | Refrigeration failure — severe temperature spike at step 20 of 30 |
| `customs_hold` | Shipment held at Frankfurt customs with delay escalation |
| `gradual_drift` | Temperature slowly drifts toward breach from step 10 onward |
| `compound_failure` | Temperature spike mid-route + customs hold near Frankfurt |

Each scenario produces a list of `TelemetryReading` objects with realistic GPS coordinates, altitude, humidity, and shock values.

---

### `src/tools/` — Domain Tools

Standalone functions given to Claude agents as callable tools:

| Tool | File | Description |
|---|---|---|
| `calculate_spoilage_probability` | `spoilage.py` | Arrhenius-inspired model: temp excursion × duration |
| `get_route_eta` | `routing.py` | Returns remaining route time for a shipment |
| `check_compliance_rules` | `compliance_rules.py` | GDP/FDA rule lookup |
| `book_cold_storage` | `storage.py` | Cold storage availability + booking |
| `send_notification` | `notifications.py` | Notification dispatch |
| `file_insurance_claim` | `claims.py` | Insurance claim initiation |

---

## Project Structure

```
AgenticAI/
├── .env.example              # Configuration template — copy to .env
├── docker-compose.yml        # One-command local deployment
├── Dockerfile
├── requirements.txt
├── pytest.ini
│
├── src/
│   ├── runtime_config.py     # Env loading, demo-mode detection
│   │
│   ├── graph/
│   │   ├── state.py          # CargoState TypedDict + Pydantic models
│   │   └── cargo_graph.py    # LangGraph graph definition
│   │
│   ├── agents/
│   │   ├── monitor.py        # Threshold monitoring (deterministic)
│   │   ├── predictor.py      # Linear regression forecasting (numpy)
│   │   ├── anomaly_detector.py   # Z-score + Claude classification
│   │   ├── risk_assessor.py  # Claude with tool use
│   │   ├── orchestrator.py   # Claude with extended thinking
│   │   ├── route_optimizer.py
│   │   ├── notification.py
│   │   ├── cold_storage.py
│   │   ├── insurance.py
│   │   ├── inventory.py
│   │   ├── compliance.py
│   │   └── demo_responses.py # Pre-scripted responses for demo mode
│   │
│   ├── api/
│   │   └── main.py           # FastAPI app — all REST endpoints
│   │
│   ├── dashboard/
│   │   └── app.py            # Streamlit demo UI
│   │
│   ├── simulator/
│   │   ├── telemetry.py      # Synthetic telemetry generator
│   │   └── scenarios.py      # Pre-built failure scenario scripts
│   │
│   └── tools/                # Domain tools exposed to Claude
│       ├── spoilage.py
│       ├── routing.py
│       ├── storage.py
│       ├── notifications.py
│       ├── claims.py
│       └── compliance_rules.py
│
├── tests/
│   ├── conftest.py
│   ├── test_graph.py
│   ├── test_integration.py
│   ├── test_monitor.py
│   ├── test_anomaly.py
│   ├── test_risk.py
│   ├── test_orchestrator.py
│   ├── test_action_agents.py
│   ├── test_simulator.py
│   ├── test_models.py
│   └── test_api_scenarios.py
│
└── docs/
    ├── architecture/system-architecture.md
    ├── high-level-design/HLD.md
    ├── low-level-design/LLD.md
    └── research/cold-chain-references.md
```

---

## Quick Start

### Option A: Demo Mode (no API key required)

```bash
# 1. Clone the repo
git clone https://github.com/your-username/ai-cargo-monitor.git
cd ai-cargo-monitor

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Open .env and set:
#   DEMO_MODE=true
#   (leave ANTHROPIC_API_KEY as placeholder)

# 5. Start the API
uvicorn src.api.main:app --port 8000 --reload

# 6. In a second terminal, start the dashboard
streamlit run src/dashboard/app.py

# 7. Open http://localhost:8501 and run a scenario
```

### Option B: With Real Claude AI

```bash
# Same steps as above, but in .env:
ANTHROPIC_API_KEY=sk-ant-your-real-key-here
DEMO_MODE=false
```

Get your API key at [console.anthropic.com](https://console.anthropic.com/).

### Option C: Docker Compose (one command)

```bash
# Set your API key in .env first, then:
docker-compose up

# API:       http://localhost:8000
# Dashboard: http://localhost:8501
```

---

## Running the Demo

### Via the Streamlit Dashboard

1. Open `http://localhost:8501`
2. In the sidebar, enter a Shipment ID (e.g. `SHP-DEMO-001`)
3. Select a scenario from the dropdown:
   - **Temp Spike** — watch the system detect a refrigeration failure and trigger REROUTE + COLD_STORAGE
   - **Customs Hold** — see CUSTOMS_ESCALATE + NOTIFY_HOSPITALS fire
   - **Gradual Drift** — observe the Predictor Agent warn of a breach 8 minutes before it happens
   - **Compound Failure** — all agents activate simultaneously
4. Click **Run Scenario**
5. Watch the agent pipeline cards light up in real time
6. When the HITL gate appears, review Claude's reasoning and click **Approve** or **Reject**

### Via the API Directly

```bash
# Initialize a shipment
curl -X POST http://localhost:8000/api/shipments/SHP-001/init

# Start the temp spike scenario in playback mode
curl -X POST "http://localhost:8000/api/scenarios/temp_spike/start/SHP-001?mode=playback&step_delay_ms=800"

# Check current status
curl http://localhost:8000/api/shipments/SHP-001/status

# Approve a pending action
curl -X POST http://localhost:8000/api/shipments/SHP-001/approve \
  -H "Content-Type: application/json" \
  -d '{"decision": "approved", "notes": "Approved via API"}'

# View the compliance audit log
curl http://localhost:8000/api/shipments/SHP-001/audit
```

---

## Human-in-the-Loop Design

When the Risk Agent classifies severity as `HIGH` or `CRITICAL`, the graph does **not** automatically proceed to action. Instead:

1. The orchestrator reasons through the incident (using extended thinking if a real API key is present)
2. The graph state is checkpointed with `awaiting_human_approval: true`
3. The API pauses the scenario and returns `awaiting_approval: true` to the dashboard
4. The Streamlit dashboard shows a prominent approval panel with:
   - Full Claude reasoning chain
   - Recommended actions with explanations
   - Approve / Reject / Modify buttons
5. The human's decision is written back into state via `graph.update_state()`
6. `graph.invoke(None, config=config)` resumes the graph from the checkpoint
7. Action agents execute in parallel

This uses LangGraph's native state persistence (`MemorySaver` checkpointer) — no external database required for demo.

---

## Testing

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/test_graph.py -v

# Run integration tests only
pytest tests/test_integration.py -v
```

All tests run in demo mode (no API key required). The `conftest.py` sets `DEMO_MODE=true` and patches the Anthropic client.

---

## Technology Stack

| Component | Technology | Version |
|---|---|---|
| Agent Framework | [LangGraph](https://github.com/langchain-ai/langgraph) | ≥ 0.2.0 |
| LLM | Claude claude-sonnet-4-6 | via Anthropic API |
| LLM SDK | [Anthropic Python SDK](https://github.com/anthropic-sdk/anthropic-python) | ≥ 0.40.0 |
| API Framework | FastAPI + Uvicorn | ≥ 0.115.0 |
| Demo Dashboard | Streamlit | ≥ 1.40.0 |
| Visualisation | Plotly | ≥ 5.24.0 |
| Data Models | Pydantic v2 | ≥ 2.9.0 |
| Numerics | NumPy | ≥ 2.1.0 |
| HTTP Client | HTTPX | ≥ 0.27.0 |
| State Persistence | LangGraph MemorySaver | built-in |
| Testing | pytest + pytest-asyncio | ≥ 8.3.0 |
| Runtime | Python | 3.11+ |

---

## Environment Variables Reference

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | *(required for live mode)* | Your Anthropic API key |
| `DEMO_MODE` | `false` | `true` = pre-scripted responses, no API key needed |
| `DATABASE_URL` | `cargo.db` | SQLite database path |
| `TELEMETRY_POLL_INTERVAL` | `30` | Seconds between telemetry readings |
| `HITL_TIMEOUT_MINUTES` | `15` | Auto-escalation timeout for human approval |
| `MAX_TELEMETRY_WINDOW` | `50` | Max readings kept in rolling window |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `DASHBOARD_PORT` | `8501` | Streamlit server port |
| `API_PORT` | `8000` | FastAPI server port |
| `LANGGRAPH_ALLOWED_MSGPACK_MODULES` | `src.graph.state` | Pydantic model deserialization whitelist |

---

## Demo Mode vs Live Mode

| Feature | Demo Mode (`DEMO_MODE=true`) | Live Mode |
|---|---|---|
| API key required | No | Yes |
| LangGraph graph executes | Yes (full pipeline) | Yes (full pipeline) |
| Claude API calls | Replaced by `demo_responses.py` | Real calls to claude-sonnet-4-6 |
| Agent tool calls | Simulated | Real function calls |
| Extended thinking visible | Pre-scripted text | Claude's real reasoning |
| Streamlit dashboard | Fully functional | Fully functional |
| Suitable for CI/CD | Yes | With key rotation |
| Cost | $0 | ~$0.01–0.05 per scenario |

Demo mode is implemented cleanly: each agent checks `USE_DEMO_MODE` (which is `True` if `DEMO_MODE=true` or if no valid API key is found) and returns from `demo_responses.py` instead of calling the Anthropic API. The rest of the agent logic — state updates, audit logging, LangGraph node completion — runs identically.

---

## GDP / Regulatory Compliance

The system is designed around pharmaceutical Good Distribution Practice (GDP) requirements:

- **Immutable audit trail**: Every agent action is appended to `audit_log` with timestamp, agent name, action type, reasoning, and GDP compliance flag. Logs are never modified, only appended (LangGraph `Annotated[list, operator.add]`).
- **WHO cold-chain thresholds**: Temperature, humidity, and shock limits sourced from WHO/GDP guidelines for vaccines and biologics.
- **GDP Article 9.2**: The orchestrator's system prompt explicitly references the regulatory obligation to notify hospitals when severity is HIGH/CRITICAL.
- **FDA 21 CFR Part 11**: Audit log format designed for electronic records compliance.
- **No real PII**: All shipment data is synthetic. No real patient data is used.

---

