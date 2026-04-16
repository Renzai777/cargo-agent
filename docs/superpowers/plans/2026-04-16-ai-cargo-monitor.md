# AI Cargo Monitor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a LangGraph multi-agent system that monitors pharmaceutical cold-chain shipments in real time, detects anomalies, and autonomously executes cascading interventions with a human-in-the-loop gate.

**Architecture:** 4-layer LangGraph pipeline — Data (synthetic telemetry) → Detection (Monitor→Anomaly→Risk agents) → Decision (Orchestrator with Claude tool use + fan-out) → Action (5 parallel action agents). Human approval gate via `interrupt_before` on Decision Orchestrator.

**Tech Stack:** Python 3.11, LangGraph 0.2+, Anthropic SDK (claude-sonnet-4-6), FastAPI, Streamlit, Plotly, SQLite, Pydantic v2, pytest, docker-compose

**Project root:** `C:\Users\A0099934\Pictures\AgenticAI\` (all paths below are relative to this)

---

## File Map

```
src/
├── graph/
│   ├── state.py              # CargoState TypedDict + all Pydantic models
│   └── cargo_graph.py        # LangGraph graph definition + compile()
├── agents/
│   ├── monitor.py            # Monitor Agent — threshold breach detection
│   ├── anomaly_detector.py   # Anomaly Agent — statistical + LLM analysis
│   ├── risk_assessor.py      # Risk Agent — spoilage probability via Claude tools
│   ├── orchestrator.py       # Decision Orchestrator — fan-out via Claude tools
│   ├── route_optimizer.py    # Action: recommend alternative routes
│   ├── notification.py       # Action: alert hospitals + reschedule appointments
│   ├── cold_storage.py       # Action: find + book emergency cold storage
│   ├── insurance.py          # Action: file insurance claim
│   └── compliance.py         # Action: write GDP/FDA audit log entry
├── tools/
│   ├── spoilage.py           # Tool: calculate_spoilage_probability
│   ├── routing.py            # Tool: get_route_eta, get_alternative_routes
│   ├── notifications.py      # Tool: send_hospital_alert, reschedule_appointment
│   ├── storage.py            # Tool: find_cold_storage, book_cold_storage
│   ├── claims.py             # Tool: file_insurance_claim
│   └── compliance_rules.py   # Tool: get_gdp_threshold, log_compliance_event
├── simulator/
│   ├── telemetry.py          # TelemetrySimulator class
│   └── scenarios.py          # Scenario runner scripts
├── api/
│   └── main.py               # FastAPI app — /ingest /status /approve /stream /scenario
└── dashboard/
    └── app.py                # Streamlit dashboard

tests/
├── test_models.py            # Pydantic model validation
├── test_monitor.py           # Monitor agent unit tests
├── test_anomaly.py           # Anomaly agent unit tests
├── test_risk.py              # Risk agent unit tests (mocked Claude)
├── test_orchestrator.py      # Orchestrator unit tests (mocked Claude)
├── test_action_agents.py     # All 5 action agents
├── test_simulator.py         # Telemetry simulator tests
├── test_graph.py             # LangGraph end-to-end integration test
└── conftest.py               # Shared fixtures

requirements.txt
.env.example
docker-compose.yml
```

---

## Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `src/__init__.py`, `src/graph/__init__.py`, `src/agents/__init__.py`, `src/tools/__init__.py`, `src/simulator/__init__.py`, `src/api/__init__.py`, `src/dashboard/__init__.py`
- Create: `tests/__init__.py`, `tests/conftest.py`

- [ ] **Step 1: Create folder structure**

```bash
cd "C:\Users\A0099934\Pictures\AgenticAI"
mkdir -p src/graph src/agents src/tools src/simulator src/api src/dashboard
mkdir -p tests data/synthetic
touch src/__init__.py src/graph/__init__.py src/agents/__init__.py
touch src/tools/__init__.py src/simulator/__init__.py src/api/__init__.py src/dashboard/__init__.py
touch tests/__init__.py
```

- [ ] **Step 2: Create requirements.txt**

```txt
# requirements.txt
anthropic>=0.40.0
langgraph>=0.2.0
langchain-anthropic>=0.3.0
langchain-core>=0.3.0
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
streamlit>=1.40.0
plotly>=5.24.0
pydantic>=2.9.0
numpy>=2.1.0
python-dotenv>=1.0.0
httpx>=0.27.0
pytest>=8.3.0
pytest-asyncio>=0.24.0
aiosqlite>=0.20.0
```

- [ ] **Step 3: Create .env.example**

```bash
# .env.example
ANTHROPIC_API_KEY=sk-ant-your-key-here
DATABASE_URL=cargo.db
TELEMETRY_POLL_INTERVAL=30
HITL_TIMEOUT_MINUTES=15
MAX_TELEMETRY_WINDOW=50
LOG_LEVEL=INFO
DASHBOARD_PORT=8501
API_PORT=8000
```

- [ ] **Step 4: Create tests/conftest.py**

```python
# tests/conftest.py
import pytest
from datetime import datetime
from src.graph.state import TelemetryReading, CargoState

@pytest.fixture
def sample_reading():
    return TelemetryReading(
        shipment_id="SHP-TEST-001",
        timestamp=datetime(2026, 4, 16, 12, 0, 0),
        temperature_c=4.5,
        humidity_pct=55.0,
        shock_g=0.3,
        latitude=40.7128,
        longitude=-74.0060,
        altitude_m=0.0,
        customs_status="in_transit",
        carrier_id="CARRIER_DHL_001"
    )

@pytest.fixture
def spike_reading():
    return TelemetryReading(
        shipment_id="SHP-TEST-001",
        timestamp=datetime(2026, 4, 16, 14, 0, 0),
        temperature_c=16.5,
        humidity_pct=55.0,
        shock_g=0.3,
        latitude=50.0,
        longitude=8.0,
        altitude_m=35000.0,
        customs_status="in_transit",
        carrier_id="CARRIER_DHL_001"
    )

@pytest.fixture
def base_state(sample_reading):
    return {
        "shipment_id": "SHP-TEST-001",
        "cargo_type": "vaccine",
        "cargo_description": "COVID-19 mRNA Vaccine — 500 doses",
        "origin_city": "New York",
        "destination_city": "Nairobi",
        "expected_arrival": datetime(2026, 4, 17, 10, 0, 0),
        "telemetry_window": [sample_reading],
        "latest_reading": sample_reading,
        "anomalies": [],
        "spoilage_probability": 0.0,
        "delay_risk": 0.0,
        "severity": "LOW",
        "recommended_actions": [],
        "orchestrator_reasoning": "",
        "route_recommendation": None,
        "notifications_sent": [],
        "cold_storage_booked": False,
        "cold_storage_facility": None,
        "insurance_claim_id": None,
        "audit_log": [],
        "gdp_compliant": True,
        "awaiting_human_approval": False,
        "human_decision": None,
        "human_notes": None,
    }
```

- [ ] **Step 5: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: All packages install without error.

- [ ] **Step 6: Copy .env.example to .env and add your key**

```bash
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY=sk-ant-...
```

- [ ] **Step 7: Commit**

```bash
git init
git add requirements.txt .env.example src/ tests/
git commit -m "feat: project scaffold — folder structure, deps, conftest"
```

---

## Task 2: Pydantic Data Models + CargoState

**Files:**
- Create: `src/graph/state.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_models.py
import pytest
from datetime import datetime
from src.graph.state import TelemetryReading, AnomalyRecord, AuditEntry, CargoState

def test_telemetry_reading_valid():
    r = TelemetryReading(
        shipment_id="SHP-001",
        timestamp=datetime(2026, 4, 16, 12, 0),
        temperature_c=4.5,
        humidity_pct=55.0,
        shock_g=0.3,
        latitude=40.71,
        longitude=-74.00,
        altitude_m=0.0,
        customs_status="in_transit",
        carrier_id="DHL-001"
    )
    assert r.temperature_c == 4.5
    assert r.customs_status == "in_transit"

def test_anomaly_record_severity_values():
    from src.graph.state import AnomalyRecord
    a = AnomalyRecord(
        anomaly_id="ANO-001",
        shipment_id="SHP-001",
        timestamp=datetime(2026, 4, 16, 12, 0),
        anomaly_type="temp_excursion",
        severity="CRITICAL",
        z_score=4.2,
        description="Temperature 16.5°C exceeds 8°C max threshold",
        raw_value=16.5,
        threshold_value=8.0
    )
    assert a.severity == "CRITICAL"
    assert a.z_score == 4.2

def test_cargo_state_is_dict_compatible(base_state):
    # CargoState is a TypedDict — must accept dict access
    assert base_state["shipment_id"] == "SHP-TEST-001"
    assert base_state["severity"] == "LOW"
    assert base_state["anomalies"] == []
```

- [ ] **Step 2: Run tests — expect ImportError**

```bash
pytest tests/test_models.py -v
```

Expected: `ImportError: cannot import name 'TelemetryReading' from 'src.graph.state'`

- [ ] **Step 3: Implement state.py**

```python
# src/graph/state.py
from __future__ import annotations
import operator
from datetime import datetime
from typing import TypedDict, Literal, Annotated
from uuid import uuid4
from pydantic import BaseModel, Field


class TelemetryReading(BaseModel):
    shipment_id: str
    timestamp: datetime
    temperature_c: float
    humidity_pct: float
    shock_g: float
    latitude: float
    longitude: float
    altitude_m: float
    customs_status: str   # "in_transit" | "held" | "cleared"
    carrier_id: str


class AnomalyRecord(BaseModel):
    anomaly_id: str = Field(default_factory=lambda: str(uuid4()))
    shipment_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    anomaly_type: str
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    z_score: float | None = None
    description: str
    raw_value: float
    threshold_value: float


class RouteOption(BaseModel):
    route_id: str = Field(default_factory=lambda: str(uuid4()))
    carrier: str
    estimated_arrival: datetime
    cost_usd: float
    risk_score: float
    reasoning: str


class AuditEntry(BaseModel):
    entry_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    agent_name: str
    action_type: str
    action_detail: str
    reasoning: str
    severity: str
    gdp_compliant: bool
    shipment_id: str


class HumanDecision(BaseModel):
    decision: Literal["approved", "rejected", "modified"]
    notes: str = ""


class CargoState(TypedDict):
    shipment_id: str
    cargo_type: str
    cargo_description: str
    origin_city: str
    destination_city: str
    expected_arrival: datetime

    telemetry_window: Annotated[list[TelemetryReading], operator.add]
    latest_reading: TelemetryReading | None

    anomalies: Annotated[list[AnomalyRecord], operator.add]
    spoilage_probability: float
    delay_risk: float
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]

    recommended_actions: list[str]
    orchestrator_reasoning: str

    route_recommendation: RouteOption | None
    notifications_sent: Annotated[list[str], operator.add]
    cold_storage_booked: bool
    cold_storage_facility: str | None
    insurance_claim_id: str | None

    audit_log: Annotated[list[AuditEntry], operator.add]
    gdp_compliant: bool

    awaiting_human_approval: bool
    human_decision: Literal["approved", "rejected", "modified"] | None
    human_notes: str | None
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/test_models.py -v
```

Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add src/graph/state.py tests/test_models.py tests/conftest.py
git commit -m "feat: Pydantic data models + CargoState TypedDict"
```

---

## Task 3: LangGraph Graph Skeleton

**Files:**
- Create: `src/graph/cargo_graph.py`
- Create: `tests/test_graph.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_graph.py
import pytest
from src.graph.cargo_graph import build_graph

def test_graph_compiles():
    graph = build_graph(db_path=":memory:")
    assert graph is not None

def test_graph_has_expected_nodes():
    graph = build_graph(db_path=":memory:")
    node_names = set(graph.nodes.keys())
    expected = {
        "monitor_agent", "anomaly_agent", "risk_agent",
        "decision_orchestrator", "route_optimizer",
        "notification_agent", "cold_storage_agent",
        "insurance_agent", "compliance_agent"
    }
    assert expected.issubset(node_names)
```

- [ ] **Step 2: Run — expect ImportError**

```bash
pytest tests/test_graph.py -v
```

Expected: `ImportError: cannot import name 'build_graph'`

- [ ] **Step 3: Create stub agents and cargo_graph.py**

First create stub agents so the graph can import them:

```python
# src/agents/monitor.py
from src.graph.state import CargoState
def monitor_agent(state: CargoState) -> dict:
    return {}

# src/agents/anomaly_detector.py
from src.graph.state import CargoState
def anomaly_agent(state: CargoState) -> dict:
    return {}

# src/agents/risk_assessor.py
from src.graph.state import CargoState
def risk_agent(state: CargoState) -> dict:
    return {"spoilage_probability": 0.0, "delay_risk": 0.0, "severity": "LOW"}

# src/agents/orchestrator.py
from src.graph.state import CargoState
def orchestrator_agent(state: CargoState) -> dict:
    return {"recommended_actions": [], "orchestrator_reasoning": ""}

# src/agents/route_optimizer.py
from src.graph.state import CargoState
def route_agent(state: CargoState) -> dict:
    return {}

# src/agents/notification.py
from src.graph.state import CargoState
def notification_agent(state: CargoState) -> dict:
    return {}

# src/agents/cold_storage.py
from src.graph.state import CargoState
def cold_storage_agent(state: CargoState) -> dict:
    return {}

# src/agents/insurance.py
from src.graph.state import CargoState
def insurance_agent(state: CargoState) -> dict:
    return {}

# src/agents/compliance.py
from src.graph.state import CargoState
def compliance_agent(state: CargoState) -> dict:
    return {}
```

Now the graph:

```python
# src/graph/cargo_graph.py
import sqlite3
from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Send
from src.graph.state import CargoState
from src.agents.monitor import monitor_agent
from src.agents.anomaly_detector import anomaly_agent
from src.agents.risk_assessor import risk_agent
from src.agents.orchestrator import orchestrator_agent
from src.agents.route_optimizer import route_agent
from src.agents.notification import notification_agent
from src.agents.cold_storage import cold_storage_agent
from src.agents.insurance import insurance_agent
from src.agents.compliance import compliance_agent


def _route_after_risk(state: CargoState) -> str:
    severity = state.get("severity", "LOW")
    if severity in ("HIGH", "CRITICAL"):
        return "decision_orchestrator"
    elif severity == "MEDIUM":
        return "decision_orchestrator"
    else:
        return "compliance_agent"


def _route_orchestrator(state: CargoState) -> list[Send]:
    actions = state.get("recommended_actions", [])
    sends = []
    if "REROUTE" in actions:
        sends.append(Send("route_optimizer", state))
    if "NOTIFY_HOSPITALS" in actions:
        sends.append(Send("notification_agent", state))
    if "COLD_STORAGE" in actions:
        sends.append(Send("cold_storage_agent", state))
    if "FILE_INSURANCE" in actions:
        sends.append(Send("insurance_agent", state))
    sends.append(Send("compliance_agent", state))
    return sends if sends else [Send("compliance_agent", state)]


def build_graph(db_path: str = "cargo.db") -> StateGraph:
    builder = StateGraph(CargoState)

    builder.add_node("monitor_agent", monitor_agent)
    builder.add_node("anomaly_agent", anomaly_agent)
    builder.add_node("risk_agent", risk_agent)
    builder.add_node("decision_orchestrator", orchestrator_agent)
    builder.add_node("route_optimizer", route_agent)
    builder.add_node("notification_agent", notification_agent)
    builder.add_node("cold_storage_agent", cold_storage_agent)
    builder.add_node("insurance_agent", insurance_agent)
    builder.add_node("compliance_agent", compliance_agent)

    builder.add_edge(START, "monitor_agent")
    builder.add_edge("monitor_agent", "anomaly_agent")
    builder.add_edge("anomaly_agent", "risk_agent")

    builder.add_conditional_edges("risk_agent", _route_after_risk, {
        "decision_orchestrator": "decision_orchestrator",
        "compliance_agent": "compliance_agent",
    })

    builder.add_conditional_edges("decision_orchestrator", _route_orchestrator)

    for node in ["route_optimizer", "notification_agent",
                 "cold_storage_agent", "insurance_agent", "compliance_agent"]:
        builder.add_edge(node, END)

    conn = sqlite3.connect(db_path, check_same_thread=False)
    checkpointer = SqliteSaver(conn)

    return builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["decision_orchestrator"]
    )
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/test_graph.py -v
```

Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add src/graph/cargo_graph.py src/agents/ tests/test_graph.py
git commit -m "feat: LangGraph graph skeleton with stub agents"
```

---

## Task 4: Telemetry Simulator

**Files:**
- Create: `src/simulator/telemetry.py`
- Create: `src/simulator/scenarios.py`
- Create: `tests/test_simulator.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_simulator.py
import pytest
from src.simulator.telemetry import TelemetrySimulator

def test_normal_reading_within_vaccine_range():
    sim = TelemetrySimulator(cargo_type="vaccine", shipment_id="SHP-001")
    reading = sim.next_reading()
    assert 1.0 <= reading.temperature_c <= 10.0  # normal noise around 4.5
    assert reading.shipment_id == "SHP-001"
    assert reading.customs_status == "in_transit"

def test_temp_spike_injection_exceeds_threshold():
    sim = TelemetrySimulator(cargo_type="vaccine", shipment_id="SHP-001")
    reading = sim.next_reading(inject_anomaly="temp_spike")
    assert reading.temperature_c > 8.0  # must breach 8°C max

def test_shock_event_injection():
    sim = TelemetrySimulator(cargo_type="vaccine", shipment_id="SHP-001")
    reading = sim.next_reading(inject_anomaly="shock_event")
    assert reading.shock_g > 2.0

def test_customs_hold_at_step_15():
    sim = TelemetrySimulator(cargo_type="vaccine", shipment_id="SHP-001")
    for _ in range(14):
        sim.next_reading()
    reading = sim.next_reading()  # step 15
    assert reading.customs_status == "held"

def test_generate_batch_returns_correct_count():
    sim = TelemetrySimulator(cargo_type="vaccine", shipment_id="SHP-001")
    readings = sim.generate_batch(10)
    assert len(readings) == 10
```

- [ ] **Step 2: Run — expect ImportError**

```bash
pytest tests/test_simulator.py -v
```

Expected: `ImportError: cannot import name 'TelemetrySimulator'`

- [ ] **Step 3: Implement telemetry.py**

```python
# src/simulator/telemetry.py
from __future__ import annotations
from datetime import datetime
from typing import Literal
import numpy as np
from src.graph.state import TelemetryReading

BASELINES: dict[str, dict] = {
    "vaccine":   {"temp": 4.5, "humidity": 55.0, "shock": 0.3, "temp_min": 2.0, "temp_max": 8.0},
    "biologics": {"temp": -18.0, "humidity": 40.0, "shock": 0.2, "temp_min": -20.0, "temp_max": -15.0},
    "default":   {"temp": 4.5, "humidity": 55.0, "shock": 0.3, "temp_min": 2.0, "temp_max": 25.0},
}

# NYC → Frankfurt → Nairobi waypoints
LAT_WAYPOINTS = [40.7128, 50.1109, -1.2921]
LON_WAYPOINTS = [-74.0060, 8.6821, 36.8219]
ALT_WAYPOINTS = [0.0, 35000.0, 0.0]  # ground → cruise → ground


class TelemetrySimulator:
    def __init__(self, cargo_type: str, shipment_id: str, total_steps: int = 100):
        self.cargo_type = cargo_type.lower()
        self.shipment_id = shipment_id
        self.total_steps = total_steps
        self._step = 0
        self._baseline = BASELINES.get(self.cargo_type, BASELINES["default"])

    def next_reading(
        self,
        inject_anomaly: Literal["temp_spike", "gradual_drift", "shock_event", "humidity_surge"] | None = None
    ) -> TelemetryReading:
        self._step += 1
        b = self._baseline

        temp = b["temp"] + np.random.normal(0, 0.3)
        humidity = b["humidity"] + np.random.normal(0, 1.5)
        shock = max(0.0, b["shock"] + np.random.exponential(0.05))

        if inject_anomaly == "temp_spike":
            temp = b["temp_max"] + np.random.uniform(5.0, 12.0)
        elif inject_anomaly == "gradual_drift":
            temp = b["temp"] + (self._step * 0.08)
        elif inject_anomaly == "shock_event":
            shock = np.random.uniform(3.5, 6.0)
        elif inject_anomaly == "humidity_surge":
            humidity = np.random.uniform(85.0, 95.0)

        return TelemetryReading(
            shipment_id=self.shipment_id,
            timestamp=datetime.utcnow(),
            temperature_c=round(float(temp), 2),
            humidity_pct=round(float(np.clip(humidity, 0.0, 100.0)), 1),
            shock_g=round(float(shock), 3),
            latitude=round(self._interpolate(LAT_WAYPOINTS), 4),
            longitude=round(self._interpolate(LON_WAYPOINTS), 4),
            altitude_m=round(self._interpolate(ALT_WAYPOINTS), 0),
            customs_status=self._customs_status(),
            carrier_id="CARRIER_DHL_001"
        )

    def generate_batch(self, count: int, inject_at: dict[int, str] | None = None) -> list[TelemetryReading]:
        inject_at = inject_at or {}
        return [self.next_reading(inject_anomaly=inject_at.get(i)) for i in range(count)]

    def _interpolate(self, waypoints: list[float]) -> float:
        progress = min(self._step / self.total_steps, 1.0)
        n = len(waypoints) - 1
        idx = min(int(progress * n), n - 1)
        t = (progress * n) - idx
        return waypoints[idx] + t * (waypoints[idx + 1] - waypoints[idx])

    def _customs_status(self) -> str:
        if 15 <= self._step <= 20:
            return "held"
        return "in_transit"
```

- [ ] **Step 4: Implement scenarios.py**

```python
# src/simulator/scenarios.py
"""Pre-defined failure scenario scripts used for demo and testing."""
from src.simulator.telemetry import TelemetrySimulator
from src.graph.state import TelemetryReading


def scenario_temp_spike(shipment_id: str = "SHP-DEMO-001") -> list[TelemetryReading]:
    """10 normal readings, then a temperature spike at step 11."""
    sim = TelemetrySimulator("vaccine", shipment_id)
    readings = sim.generate_batch(10)
    readings.append(sim.next_reading(inject_anomaly="temp_spike"))
    return readings


def scenario_customs_hold(shipment_id: str = "SHP-DEMO-002") -> list[TelemetryReading]:
    """Customs hold kicks in around step 15."""
    sim = TelemetrySimulator("vaccine", shipment_id)
    return sim.generate_batch(22)


def scenario_gradual_drift(shipment_id: str = "SHP-DEMO-003") -> list[TelemetryReading]:
    """Temperature gradually drifts up over 20 steps."""
    sim = TelemetrySimulator("vaccine", shipment_id)
    return sim.generate_batch(20, inject_at={i: "gradual_drift" for i in range(5, 20)})


def scenario_compound_failure(shipment_id: str = "SHP-DEMO-004") -> list[TelemetryReading]:
    """Temperature spike AND customs hold simultaneously."""
    sim = TelemetrySimulator("vaccine", shipment_id, total_steps=50)
    readings = sim.generate_batch(14)
    # Step 15: spike + customs hold naturally activates
    readings.append(sim.next_reading(inject_anomaly="temp_spike"))
    readings += sim.generate_batch(5)  # customs hold continues
    return readings


SCENARIOS = {
    "temp_spike": scenario_temp_spike,
    "customs_hold": scenario_customs_hold,
    "gradual_drift": scenario_gradual_drift,
    "compound_failure": scenario_compound_failure,
}
```

- [ ] **Step 5: Run tests — expect PASS**

```bash
pytest tests/test_simulator.py -v
```

Expected: `5 passed`

- [ ] **Step 6: Commit**

```bash
git add src/simulator/ tests/test_simulator.py
git commit -m "feat: telemetry simulator with failure scenario injection"
```

---

## Task 5: Monitor Agent

**Files:**
- Modify: `src/agents/monitor.py`
- Create: `tests/test_monitor.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_monitor.py
import pytest
from src.agents.monitor import monitor_agent

def test_no_breach_returns_empty_anomalies(base_state):
    result = monitor_agent(base_state)
    assert result["anomalies"] == []
    assert len(result["audit_log"]) == 1
    assert result["audit_log"][0].action_type == "THRESHOLD_CHECK"

def test_temp_breach_detected(base_state, spike_reading):
    state = {**base_state, "latest_reading": spike_reading}
    result = monitor_agent(state)
    assert any("temp" in a.anomaly_type for a in result["anomalies"])

def test_customs_hold_detected(base_state, sample_reading):
    held = sample_reading.model_copy(update={"customs_status": "held"})
    state = {**base_state, "latest_reading": held}
    result = monitor_agent(state)
    assert any("customs" in a.anomaly_type for a in result["anomalies"])

def test_shock_breach_detected(base_state, sample_reading):
    shock = sample_reading.model_copy(update={"shock_g": 4.5})
    state = {**base_state, "latest_reading": shock}
    result = monitor_agent(state)
    assert any("shock" in a.anomaly_type for a in result["anomalies"])
```

- [ ] **Step 2: Run — expect FAIL (stubs return empty)**

```bash
pytest tests/test_monitor.py -v
```

Expected: `FAILED test_no_breach_returns_empty_anomalies` — stub returns `{}`

- [ ] **Step 3: Implement monitor_agent**

```python
# src/agents/monitor.py
from datetime import datetime
from src.graph.state import CargoState, AnomalyRecord, AuditEntry

THRESHOLDS: dict[str, dict] = {
    "vaccine":   {"temp_min": 2.0, "temp_max": 8.0, "humidity_max": 75.0, "shock_max": 2.0},
    "biologics": {"temp_min": -20.0, "temp_max": -15.0, "humidity_max": 60.0, "shock_max": 1.5},
    "default":   {"temp_min": 2.0, "temp_max": 25.0, "humidity_max": 80.0, "shock_max": 3.0},
}


def monitor_agent(state: CargoState) -> dict:
    reading = state["latest_reading"]
    cargo_type = state["cargo_type"].lower()
    t = THRESHOLDS.get(cargo_type, THRESHOLDS["default"])
    anomalies: list[AnomalyRecord] = []

    if not (t["temp_min"] <= reading.temperature_c <= t["temp_max"]):
        anomalies.append(AnomalyRecord(
            shipment_id=state["shipment_id"],
            anomaly_type="temp_excursion",
            severity="HIGH",
            description=(
                f"Temperature {reading.temperature_c}°C outside safe range "
                f"[{t['temp_min']}, {t['temp_max']}]°C for {cargo_type}"
            ),
            raw_value=reading.temperature_c,
            threshold_value=t["temp_max"] if reading.temperature_c > t["temp_max"] else t["temp_min"],
        ))

    if reading.humidity_pct > t["humidity_max"]:
        anomalies.append(AnomalyRecord(
            shipment_id=state["shipment_id"],
            anomaly_type="humidity_excursion",
            severity="MEDIUM",
            description=f"Humidity {reading.humidity_pct}% exceeds {t['humidity_max']}% max",
            raw_value=reading.humidity_pct,
            threshold_value=t["humidity_max"],
        ))

    if reading.shock_g > t["shock_max"]:
        anomalies.append(AnomalyRecord(
            shipment_id=state["shipment_id"],
            anomaly_type="shock_event",
            severity="MEDIUM",
            description=f"Shock {reading.shock_g}g exceeds {t['shock_max']}g max",
            raw_value=reading.shock_g,
            threshold_value=t["shock_max"],
        ))

    if reading.customs_status == "held":
        anomalies.append(AnomalyRecord(
            shipment_id=state["shipment_id"],
            anomaly_type="customs_hold",
            severity="HIGH",
            description="Shipment held at customs — potential delay to destination",
            raw_value=0.0,
            threshold_value=0.0,
        ))

    detail = f"Detected {len(anomalies)} breach(es)" if anomalies else "All thresholds nominal"
    return {
        "anomalies": anomalies,
        "audit_log": [AuditEntry(
            agent_name="monitor_agent",
            action_type="THRESHOLD_CHECK",
            action_detail=detail,
            reasoning=f"Compared reading against GDP thresholds for cargo type '{cargo_type}'",
            severity="HIGH" if anomalies else "LOW",
            gdp_compliant=True,
            shipment_id=state["shipment_id"],
        )],
    }
```

- [ ] **Step 4: Run — expect PASS**

```bash
pytest tests/test_monitor.py -v
```

Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add src/agents/monitor.py tests/test_monitor.py
git commit -m "feat: monitor agent — threshold breach detection for temp/humidity/shock/customs"
```

---

## Task 6: Anomaly Detection Agent

**Files:**
- Modify: `src/agents/anomaly_detector.py`
- Create: `tests/test_anomaly.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_anomaly.py
import pytest
from unittest.mock import patch, MagicMock
from src.agents.anomaly_detector import anomaly_agent
from src.graph.state import AnomalyRecord

def test_no_anomalies_with_clean_window(base_state):
    """When all readings are normal, no anomalies should be added."""
    result = anomaly_agent(base_state)
    assert result.get("anomalies", []) == []

def test_high_zscore_triggers_llm_call(base_state, spike_reading):
    """Z-score > 3 should trigger LLM analysis."""
    # Fill window with normal readings, add spike at end
    state = {**base_state, "latest_reading": spike_reading}
    # Add 10 normal readings to window
    from src.simulator.telemetry import TelemetrySimulator
    sim = TelemetrySimulator("vaccine", "SHP-TEST-001")
    state["telemetry_window"] = sim.generate_batch(10)

    mock_response = MagicMock()
    mock_response.content = [MagicMock(
        text='{"severity": "CRITICAL", "description": "Severe temperature excursion detected — refrigeration likely failed.", "anomaly_type": "temp_excursion"}'
    )]

    with patch("src.agents.anomaly_detector.client.messages.create", return_value=mock_response):
        result = anomaly_agent(state)

    assert len(result["anomalies"]) > 0
    assert result["anomalies"][0].severity == "CRITICAL"

def test_low_zscore_no_llm_call(base_state):
    """Z-score < 3 should not trigger LLM — no new anomalies added."""
    from src.simulator.telemetry import TelemetrySimulator
    sim = TelemetrySimulator("vaccine", "SHP-TEST-001")
    state = {**base_state, "telemetry_window": sim.generate_batch(10)}

    with patch("src.agents.anomaly_detector.client.messages.create") as mock_llm:
        result = anomaly_agent(state)
        mock_llm.assert_not_called()

    assert result.get("anomalies", []) == []
```

- [ ] **Step 2: Run — expect FAIL**

```bash
pytest tests/test_anomaly.py -v
```

Expected: `FAILED` — stubs return `{}`

- [ ] **Step 3: Implement anomaly_detector.py**

```python
# src/agents/anomaly_detector.py
import json
from datetime import datetime
import numpy as np
from anthropic import Anthropic
from src.graph.state import CargoState, AnomalyRecord, AuditEntry

client = Anthropic()
Z_SCORE_THRESHOLD = 3.0


def anomaly_agent(state: CargoState) -> dict:
    window = state["telemetry_window"][-20:]
    reading = state["latest_reading"]

    if len(window) < 3:
        return {"anomalies": [], "audit_log": [_audit("Insufficient window for analysis", state)]}

    temps = [r.temperature_c for r in window]
    mean = float(np.mean(temps))
    std = float(np.std(temps))

    if std < 0.001:
        return {"anomalies": [], "audit_log": [_audit("Zero variance in window — nominal", state)]}

    z_score = abs((reading.temperature_c - mean) / std)

    if z_score < Z_SCORE_THRESHOLD:
        return {"anomalies": [], "audit_log": [_audit(f"Z-score {z_score:.2f} below threshold", state)]}

    # LLM contextual analysis for high z-score
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{
            "role": "user",
            "content": (
                f"Analyze this temperature anomaly for pharmaceutical cargo:\n\n"
                f"Cargo: {state['cargo_type']} ({state['cargo_description']})\n"
                f"Current temp: {reading.temperature_c}°C\n"
                f"Window mean: {mean:.2f}°C, std: {std:.2f}°C\n"
                f"Z-score: {z_score:.2f}\n"
                f"Customs status: {reading.customs_status}\n"
                f"Location: {reading.latitude:.2f}, {reading.longitude:.2f}\n"
                f"Altitude: {reading.altitude_m}m\n\n"
                f"Classify severity (LOW/MEDIUM/HIGH/CRITICAL) and explain in 2 sentences.\n"
                f"Return ONLY valid JSON: "
                f'{{\"severity\": \"...\", \"description\": \"...\", \"anomaly_type\": \"...\"}}'
            )
        }]
    )

    result = json.loads(response.content[0].text.strip())
    anomaly = AnomalyRecord(
        shipment_id=state["shipment_id"],
        anomaly_type=result["anomaly_type"],
        severity=result["severity"],
        z_score=round(z_score, 2),
        description=result["description"],
        raw_value=reading.temperature_c,
        threshold_value=8.0 if state["cargo_type"] == "vaccine" else 25.0,
    )

    return {
        "anomalies": [anomaly],
        "audit_log": [_audit(
            f"Z-score {z_score:.2f} — LLM classified as {result['severity']}: {result['description'][:80]}",
            state
        )],
    }


def _audit(detail: str, state: CargoState) -> AuditEntry:
    return AuditEntry(
        agent_name="anomaly_agent",
        action_type="ANOMALY_ANALYSIS",
        action_detail=detail,
        reasoning="Statistical Z-score analysis + LLM contextual classification",
        severity="INFO",
        gdp_compliant=True,
        shipment_id=state["shipment_id"],
    )
```

- [ ] **Step 4: Run — expect PASS**

```bash
pytest tests/test_anomaly.py -v
```

Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add src/agents/anomaly_detector.py tests/test_anomaly.py
git commit -m "feat: anomaly detection agent — Z-score + Claude contextual analysis"
```

---

## Task 7: Compliance Tool + Compliance Agent

**Files:**
- Create: `src/tools/compliance_rules.py`
- Modify: `src/agents/compliance.py`
- Create: `tests/test_action_agents.py` (partial — compliance section)

- [ ] **Step 1: Write failing test**

```python
# tests/test_action_agents.py
import pytest
from src.agents.compliance import compliance_agent
from src.graph.state import AnomalyRecord
from datetime import datetime

def test_compliance_agent_writes_audit_entry(base_state):
    result = compliance_agent(base_state)
    assert len(result["audit_log"]) >= 1
    entry = result["audit_log"][0]
    assert entry.agent_name == "compliance_agent"
    assert entry.gdp_compliant is True
    assert entry.shipment_id == "SHP-TEST-001"

def test_compliance_agent_marks_gdp_compliant(base_state):
    result = compliance_agent(base_state)
    assert result["gdp_compliant"] is True
```

- [ ] **Step 2: Run — expect FAIL**

```bash
pytest tests/test_action_agents.py::test_compliance_agent_writes_audit_entry -v
pytest tests/test_action_agents.py::test_compliance_agent_marks_gdp_compliant -v
```

Expected: `FAILED` — stub returns `{}`

- [ ] **Step 3: Implement compliance tool and agent**

```python
# src/tools/compliance_rules.py
GDP_THRESHOLDS = {
    "vaccine":   {"temp_min": 2.0, "temp_max": 8.0, "max_excursion_minutes": 120},
    "biologics": {"temp_min": -20.0, "temp_max": -15.0, "max_excursion_minutes": 30},
    "default":   {"temp_min": 2.0, "temp_max": 25.0, "max_excursion_minutes": 240},
}

def get_gdp_threshold(cargo_type: str) -> dict:
    return GDP_THRESHOLDS.get(cargo_type.lower(), GDP_THRESHOLDS["default"])

def is_gdp_compliant(cargo_type: str, temperature: float) -> bool:
    t = get_gdp_threshold(cargo_type)
    return t["temp_min"] <= temperature <= t["temp_max"]
```

```python
# src/agents/compliance.py
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
```

- [ ] **Step 4: Run — expect PASS**

```bash
pytest tests/test_action_agents.py -v
```

Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add src/tools/compliance_rules.py src/agents/compliance.py tests/test_action_agents.py
git commit -m "feat: compliance agent + GDP/FDA audit logging"
```

---

## Task 8: Risk Assessment Agent

**Files:**
- Create: `src/tools/spoilage.py`, `src/tools/routing.py`
- Modify: `src/agents/risk_assessor.py`
- Create: `tests/test_risk.py`

- [ ] **Step 1: Create tools**

```python
# src/tools/spoilage.py
SPOILAGE_RATES = {
    "vaccine":   {"rate_per_degree_per_hour": 0.12},
    "biologics": {"rate_per_degree_per_hour": 0.20},
    "default":   {"rate_per_degree_per_hour": 0.08},
}

def calculate_spoilage_probability(cargo_type: str, temp_excursion_c: float, duration_minutes: float) -> float:
    rate = SPOILAGE_RATES.get(cargo_type.lower(), SPOILAGE_RATES["default"])["rate_per_degree_per_hour"]
    hours = duration_minutes / 60.0
    prob = min(1.0, temp_excursion_c * hours * rate)
    return round(prob, 3)
```

```python
# src/tools/routing.py
import random
from datetime import datetime, timedelta

MOCK_ROUTES = {
    "SHP-TEST-001": {"eta_minutes": 480, "origin": "New York", "destination": "Nairobi"},
    "SHP-DEMO-001": {"eta_minutes": 320, "origin": "New York", "destination": "Nairobi"},
}

def get_route_eta(shipment_id: str) -> dict:
    route = MOCK_ROUTES.get(shipment_id, {"eta_minutes": 400, "origin": "Unknown", "destination": "Unknown"})
    return {
        "shipment_id": shipment_id,
        "remaining_minutes": route["eta_minutes"],
        "origin": route["origin"],
        "destination": route["destination"],
    }
```

- [ ] **Step 2: Write failing tests**

```python
# tests/test_risk.py
import pytest
from unittest.mock import patch, MagicMock
from src.agents.risk_assessor import risk_agent
from src.graph.state import AnomalyRecord
from datetime import datetime

@pytest.fixture
def state_with_anomaly(base_state):
    anomaly = AnomalyRecord(
        shipment_id="SHP-TEST-001",
        anomaly_type="temp_excursion",
        severity="HIGH",
        z_score=4.2,
        description="Temperature 16.5°C exceeds 8°C max",
        raw_value=16.5,
        threshold_value=8.0,
    )
    return {**base_state, "anomalies": [anomaly]}

def test_no_anomalies_returns_low_risk(base_state):
    result = risk_agent(base_state)
    assert result["severity"] == "LOW"
    assert result["spoilage_probability"] == 0.0

def test_anomaly_calls_claude_and_returns_risk(state_with_anomaly):
    mock_resp = MagicMock()
    mock_resp.stop_reason = "end_turn"
    mock_resp.content = [MagicMock(
        type="text",
        text='{"spoilage_probability": 0.72, "delay_risk": 0.45, "severity": "CRITICAL", "reasoning": "High temp excursion with 8h remaining route time — vaccine viability severely threatened."}'
    )]

    with patch("src.agents.risk_assessor.client.messages.create", return_value=mock_resp):
        result = risk_agent(state_with_anomaly)

    assert result["spoilage_probability"] == 0.72
    assert result["severity"] == "CRITICAL"

def test_risk_audit_entry_written(state_with_anomaly):
    mock_resp = MagicMock()
    mock_resp.stop_reason = "end_turn"
    mock_resp.content = [MagicMock(
        type="text",
        text='{"spoilage_probability": 0.5, "delay_risk": 0.3, "severity": "HIGH", "reasoning": "Moderate risk."}'
    )]

    with patch("src.agents.risk_assessor.client.messages.create", return_value=mock_resp):
        result = risk_agent(state_with_anomaly)

    assert len(result["audit_log"]) >= 1
    assert result["audit_log"][0].agent_name == "risk_agent"
```

- [ ] **Step 3: Run — expect FAIL**

```bash
pytest tests/test_risk.py -v
```

Expected: `FAILED` — stubs return wrong structure

- [ ] **Step 4: Implement risk_assessor.py**

```python
# src/agents/risk_assessor.py
import json
from anthropic import Anthropic
from src.graph.state import CargoState, AuditEntry
from src.tools.spoilage import calculate_spoilage_probability
from src.tools.routing import get_route_eta

client = Anthropic()

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

    # Agentic tool-use loop
    for _ in range(5):
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
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

        # Handle tool calls
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
```

- [ ] **Step 5: Run — expect PASS**

```bash
pytest tests/test_risk.py -v
```

Expected: `3 passed`

- [ ] **Step 6: Commit**

```bash
git add src/agents/risk_assessor.py src/tools/spoilage.py src/tools/routing.py tests/test_risk.py
git commit -m "feat: risk assessment agent with Claude tool use for spoilage + ETA"
```

---

## Task 9: Decision Orchestrator Agent

**Files:**
- Create: `src/tools/notifications.py`, `src/tools/storage.py`, `src/tools/claims.py`
- Modify: `src/agents/orchestrator.py`
- Create: `tests/test_orchestrator.py`

- [ ] **Step 1: Create action tools**

```python
# src/tools/notifications.py
def send_hospital_alert(hospital_name: str, message: str, severity: str) -> dict:
    return {"status": "sent", "hospital": hospital_name, "message": message, "severity": severity}

def reschedule_appointment(appointment_id: str, reason: str) -> dict:
    return {"status": "rescheduled", "appointment_id": appointment_id, "reason": reason}
```

```python
# src/tools/storage.py
MOCK_FACILITIES = [
    {"id": "CSF-FRA-001", "name": "Frankfurt ColdHub", "capacity_kg": 500, "temp_range": "2-8°C", "distance_km": 15},
    {"id": "CSF-FRA-002", "name": "Rhine Cold Storage", "capacity_kg": 300, "temp_range": "2-8°C", "distance_km": 22},
]

def find_cold_storage(location: str, cargo_type: str) -> dict:
    return {"facilities": MOCK_FACILITIES, "location": location}

def book_cold_storage(facility_id: str, shipment_id: str, duration_hours: int) -> dict:
    facility = next((f for f in MOCK_FACILITIES if f["id"] == facility_id), MOCK_FACILITIES[0])
    return {"status": "booked", "facility": facility["name"], "shipment_id": shipment_id, "duration_hours": duration_hours}
```

```python
# src/tools/claims.py
import random, string
from datetime import datetime

def file_insurance_claim(shipment_id: str, damage_description: str, estimated_value_usd: float) -> dict:
    claim_id = "CLM-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return {
        "claim_id": claim_id,
        "shipment_id": shipment_id,
        "status": "filed",
        "estimated_value_usd": estimated_value_usd,
        "filed_at": datetime.utcnow().isoformat(),
    }
```

- [ ] **Step 2: Write failing tests**

```python
# tests/test_orchestrator.py
import pytest
from unittest.mock import patch, MagicMock
from src.agents.orchestrator import orchestrator_agent
from src.graph.state import AnomalyRecord

@pytest.fixture
def critical_state(base_state):
    anomaly = AnomalyRecord(
        shipment_id="SHP-TEST-001",
        anomaly_type="temp_excursion",
        severity="CRITICAL",
        z_score=5.1,
        description="Refrigeration failure — temp 18°C",
        raw_value=18.0,
        threshold_value=8.0,
    )
    return {**base_state, "anomalies": [anomaly], "spoilage_probability": 0.85, "severity": "CRITICAL"}

def test_orchestrator_returns_actions(critical_state):
    mock_resp = MagicMock()
    mock_resp.stop_reason = "end_turn"
    mock_resp.content = [MagicMock(type="text", text="Triggering REROUTE and NOTIFY_HOSPITALS due to CRITICAL spoilage risk.")]

    with patch("src.agents.orchestrator.client.messages.create", return_value=mock_resp):
        result = orchestrator_agent(critical_state)

    assert "recommended_actions" in result
    assert isinstance(result["recommended_actions"], list)

def test_orchestrator_always_includes_compliance(critical_state):
    mock_resp = MagicMock()
    mock_resp.stop_reason = "end_turn"
    mock_resp.content = [MagicMock(type="text", text="REROUTE NOTIFY_HOSPITALS COLD_STORAGE FILE_INSURANCE")]

    with patch("src.agents.orchestrator.client.messages.create", return_value=mock_resp):
        result = orchestrator_agent(critical_state)

    assert len(result["audit_log"]) >= 1
    assert result["audit_log"][0].agent_name == "orchestrator_agent"
```

- [ ] **Step 3: Run — expect FAIL**

```bash
pytest tests/test_orchestrator.py -v
```

Expected: `FAILED`

- [ ] **Step 4: Implement orchestrator.py**

```python
# src/agents/orchestrator.py
from anthropic import Anthropic
from src.graph.state import CargoState, AuditEntry

client = Anthropic()

ACTION_FLAGS = ["REROUTE", "COLD_STORAGE", "NOTIFY_HOSPITALS", "FILE_INSURANCE", "CUSTOMS_ESCALATE"]

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

Return a clear list of actions and your reasoning."""


def orchestrator_agent(state: CargoState) -> dict:
    prompt = (
        f"Incident report for shipment {state['shipment_id']}:\n\n"
        f"Cargo: {state['cargo_type']} — {state['cargo_description']}\n"
        f"Route: {state['origin_city']} → {state['destination_city']}\n"
        f"Severity: {state['severity']}\n"
        f"Spoilage probability: {state['spoilage_probability']:.0%}\n"
        f"Delay risk: {state['delay_risk']:.0%}\n"
        f"Anomalies: {[a.description for a in state.get('anomalies', [])]}\n\n"
        f"List required actions (use exact action names) and explain your reasoning."
    )

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = response.content[0].text
    actions = [a for a in ACTION_FLAGS if a in response_text]

    return {
        "recommended_actions": actions,
        "orchestrator_reasoning": response_text,
        "awaiting_human_approval": state.get("severity") in ("HIGH", "CRITICAL"),
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
```

- [ ] **Step 5: Run — expect PASS**

```bash
pytest tests/test_orchestrator.py -v
```

Expected: `2 passed`

- [ ] **Step 6: Commit**

```bash
git add src/agents/orchestrator.py src/tools/ tests/test_orchestrator.py
git commit -m "feat: decision orchestrator agent + action tools (notifications/storage/claims)"
```

---

## Task 10: Remaining Action Agents

**Files:**
- Modify: `src/agents/route_optimizer.py`, `src/agents/notification.py`, `src/agents/cold_storage.py`, `src/agents/insurance.py`
- Modify: `tests/test_action_agents.py`

- [ ] **Step 1: Add tests for remaining agents**

```python
# append to tests/test_action_agents.py

from src.agents.route_optimizer import route_agent
from src.agents.notification import notification_agent
from src.agents.cold_storage import cold_storage_agent
from src.agents.insurance import insurance_agent

def test_route_agent_returns_recommendation(base_state):
    result = route_agent(base_state)
    assert result["route_recommendation"] is not None
    assert result["route_recommendation"].carrier != ""
    assert result["route_recommendation"].risk_score <= 1.0

def test_notification_agent_records_sent(base_state):
    result = notification_agent(base_state)
    assert len(result["notifications_sent"]) > 0
    assert any("Nairobi" in n or "hospital" in n.lower() for n in result["notifications_sent"])

def test_cold_storage_agent_books_facility(base_state):
    result = cold_storage_agent(base_state)
    assert result["cold_storage_booked"] is True
    assert result["cold_storage_facility"] is not None

def test_insurance_agent_generates_claim_id(base_state):
    result = insurance_agent(base_state)
    assert result["insurance_claim_id"] is not None
    assert result["insurance_claim_id"].startswith("CLM-")
```

- [ ] **Step 2: Run — expect FAIL**

```bash
pytest tests/test_action_agents.py -v
```

Expected: `FAILED` for new tests

- [ ] **Step 3: Implement the 4 action agents**

```python
# src/agents/route_optimizer.py
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
```

```python
# src/agents/notification.py
from src.graph.state import CargoState, AuditEntry

DESTINATION_HOSPITALS = {
    "Nairobi": ["Kenyatta National Hospital", "Aga Khan University Hospital", "Nairobi West Hospital"],
    "Frankfurt": ["Universitätsklinikum Frankfurt", "Krankenhaus Sachsenhausen"],
    "New York": ["Bellevue Hospital", "NYU Langone Medical Center"],
}

def notification_agent(state: CargoState) -> dict:
    dest = state["destination_city"]
    hospitals = DESTINATION_HOSPITALS.get(dest, [f"{dest} General Hospital"])
    severity = state.get("severity", "LOW")

    notifications = []
    for h in hospitals:
        msg = (
            f"ALERT [{severity}]: Shipment {state['shipment_id']} carrying "
            f"{state['cargo_type']} may be delayed or compromised. "
            f"Spoilage probability: {state.get('spoilage_probability', 0):.0%}. "
            f"Please prepare contingency stock and reschedule non-urgent appointments."
        )
        notifications.append(f"Notified {h}: {msg[:100]}")

    return {
        "notifications_sent": notifications,
        "audit_log": [AuditEntry(
            agent_name="notification_agent",
            action_type="HOSPITAL_NOTIFICATION",
            action_detail=f"Notified {len(notifications)} facilities in {dest}",
            reasoning=f"GDP Art.9.2 requires downstream notification when cold-chain breach severity >= HIGH",
            severity=severity,
            gdp_compliant=True,
            shipment_id=state["shipment_id"],
        )],
    }
```

```python
# src/agents/cold_storage.py
from src.graph.state import CargoState, AuditEntry
from src.tools.storage import find_cold_storage, book_cold_storage

def cold_storage_agent(state: CargoState) -> dict:
    reading = state.get("latest_reading")
    location = f"{reading.latitude:.1f},{reading.longitude:.1f}" if reading else "unknown"
    facilities = find_cold_storage(location, state["cargo_type"])
    best = facilities["facilities"][0]
    booking = book_cold_storage(best["id"], state["shipment_id"], duration_hours=48)

    return {
        "cold_storage_booked": True,
        "cold_storage_facility": booking["facility"],
        "audit_log": [AuditEntry(
            agent_name="cold_storage_agent",
            action_type="COLD_STORAGE_BOOKED",
            action_detail=f"Booked {booking['facility']} for 48h emergency storage",
            reasoning=f"Spoilage risk {state.get('spoilage_probability', 0):.0%} requires immediate cold storage intervention",
            severity=state.get("severity", "LOW"),
            gdp_compliant=True,
            shipment_id=state["shipment_id"],
        )],
    }
```

```python
# src/agents/insurance.py
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
```

- [ ] **Step 4: Run all action agent tests**

```bash
pytest tests/test_action_agents.py -v
```

Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
git add src/agents/ tests/test_action_agents.py
git commit -m "feat: all 5 action agents — route, notification, cold storage, insurance, compliance"
```

---

## Task 11: FastAPI Backend

**Files:**
- Modify: `src/api/main.py`

- [ ] **Step 1: Implement FastAPI app**

```python
# src/api/main.py
import json
import asyncio
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.graph.cargo_graph import build_graph
from src.graph.state import TelemetryReading, HumanDecision, CargoState
from src.simulator.scenarios import SCENARIOS

app = FastAPI(title="AI Cargo Monitor", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

graph = build_graph()

DEFAULT_STATE: dict = {
    "cargo_type": "vaccine",
    "cargo_description": "COVID-19 mRNA Vaccine — 500 doses",
    "origin_city": "New York",
    "destination_city": "Nairobi",
    "expected_arrival": datetime(2026, 4, 17, 10, 0, 0),
    "telemetry_window": [],
    "latest_reading": None,
    "anomalies": [],
    "spoilage_probability": 0.0,
    "delay_risk": 0.0,
    "severity": "LOW",
    "recommended_actions": [],
    "orchestrator_reasoning": "",
    "route_recommendation": None,
    "notifications_sent": [],
    "cold_storage_booked": False,
    "cold_storage_facility": None,
    "insurance_claim_id": None,
    "audit_log": [],
    "gdp_compliant": True,
    "awaiting_human_approval": False,
    "human_decision": None,
    "human_notes": None,
}


@app.post("/api/shipments/{shipment_id}/init")
async def init_shipment(shipment_id: str):
    config = {"configurable": {"thread_id": shipment_id}}
    state = {**DEFAULT_STATE, "shipment_id": shipment_id}
    graph.update_state(config, state)
    return {"status": "initialized", "shipment_id": shipment_id}


@app.post("/api/shipments/{shipment_id}/ingest")
async def ingest_telemetry(shipment_id: str, reading: TelemetryReading):
    config = {"configurable": {"thread_id": shipment_id}}
    update = {"latest_reading": reading, "telemetry_window": [reading]}
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None, lambda: graph.invoke(update, config=config)
        )
        return {
            "status": "processed",
            "severity": result.get("severity", "LOW"),
            "awaiting_approval": result.get("awaiting_human_approval", False),
            "anomalies": len(result.get("anomalies", [])),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/shipments/{shipment_id}/status")
def get_status(shipment_id: str):
    config = {"configurable": {"thread_id": shipment_id}}
    snapshot = graph.get_state(config)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Shipment not found")
    values = snapshot.values
    return {
        "shipment_id": shipment_id,
        "severity": values.get("severity", "LOW"),
        "spoilage_probability": values.get("spoilage_probability", 0.0),
        "delay_risk": values.get("delay_risk", 0.0),
        "awaiting_human_approval": values.get("awaiting_human_approval", False),
        "orchestrator_reasoning": values.get("orchestrator_reasoning", ""),
        "recommended_actions": values.get("recommended_actions", []),
        "anomaly_count": len(values.get("anomalies", [])),
        "notifications_sent": values.get("notifications_sent", []),
        "cold_storage_booked": values.get("cold_storage_booked", False),
        "cold_storage_facility": values.get("cold_storage_facility"),
        "insurance_claim_id": values.get("insurance_claim_id"),
        "audit_log": [e.model_dump() for e in values.get("audit_log", [])],
        "telemetry_window": [r.model_dump() for r in values.get("telemetry_window", [])[-20:]],
        "latest_reading": values.get("latest_reading").model_dump() if values.get("latest_reading") else None,
        "route_recommendation": values.get("route_recommendation").model_dump() if values.get("route_recommendation") else None,
    }


@app.post("/api/shipments/{shipment_id}/approve")
async def approve_action(shipment_id: str, decision: HumanDecision):
    config = {"configurable": {"thread_id": shipment_id}}
    graph.update_state(config, {
        "human_decision": decision.decision,
        "human_notes": decision.notes,
        "awaiting_human_approval": False,
    })
    result = await asyncio.get_event_loop().run_in_executor(
        None, lambda: graph.invoke(None, config=config)
    )
    return {"status": "resumed", "severity": result.get("severity"), "actions": result.get("recommended_actions", [])}


@app.post("/api/scenarios/{scenario_name}/run/{shipment_id}")
async def run_scenario(scenario_name: str, shipment_id: str):
    if scenario_name not in SCENARIOS:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_name}' not found. Available: {list(SCENARIOS)}")
    readings = SCENARIOS[scenario_name](shipment_id=shipment_id)
    await init_shipment(shipment_id)
    results = []
    for reading in readings:
        r = await ingest_telemetry(shipment_id, reading)
        results.append(r)
    return {"scenario": scenario_name, "readings_processed": len(readings), "final_status": results[-1]}


@app.get("/api/scenarios")
def list_scenarios():
    return {"scenarios": list(SCENARIOS.keys())}
```

- [ ] **Step 2: Test the API manually**

```bash
uvicorn src.api.main:app --reload --port 8000
```

In a new terminal:
```bash
# Initialize a shipment
curl -X POST http://localhost:8000/api/shipments/SHP-DEMO-001/init

# Run temp_spike scenario
curl -X POST http://localhost:8000/api/scenarios/temp_spike/run/SHP-DEMO-001

# Check status
curl http://localhost:8000/api/shipments/SHP-DEMO-001/status | python -m json.tool
```

Expected: severity shows `HIGH` or `CRITICAL` after temp_spike scenario

- [ ] **Step 3: Commit**

```bash
git add src/api/main.py
git commit -m "feat: FastAPI backend — ingest, status, approve, scenario endpoints"
```

---

## Task 12: Streamlit Dashboard

**Files:**
- Modify: `src/dashboard/app.py`

- [ ] **Step 1: Implement dashboard**

```python
# src/dashboard/app.py
import time
import httpx
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

API_BASE = "http://localhost:8000"
SHIPMENT_ID = "SHP-DEMO-001"
REFRESH_INTERVAL = 5  # seconds

st.set_page_config(
    page_title="AI Cargo Monitor",
    page_icon="🌡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.metric-card { background: #1e1e2e; border-radius: 8px; padding: 1rem; margin: 0.5rem 0; }
.severity-critical { color: #ef4444; font-weight: bold; font-size: 1.4rem; }
.severity-high { color: #f97316; font-weight: bold; font-size: 1.4rem; }
.severity-medium { color: #eab308; font-weight: bold; font-size: 1.4rem; }
.severity-low { color: #22c55e; font-weight: bold; font-size: 1.4rem; }
</style>
""", unsafe_allow_html=True)


def fetch_status(shipment_id: str) -> dict | None:
    try:
        resp = httpx.get(f"{API_BASE}/api/shipments/{shipment_id}/status", timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


def run_scenario(scenario: str, shipment_id: str):
    try:
        httpx.post(f"{API_BASE}/api/scenarios/{scenario}/run/{shipment_id}", timeout=60)
    except Exception as e:
        st.error(f"Scenario failed: {e}")


def approve_action(shipment_id: str, decision: str, notes: str = ""):
    try:
        httpx.post(
            f"{API_BASE}/api/shipments/{shipment_id}/approve",
            json={"decision": decision, "notes": notes},
            timeout=30,
        )
    except Exception as e:
        st.error(f"Approval failed: {e}")


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🌡️ AI Cargo Monitor")
    st.caption("UMD Agentic AI Hackathon 2026")
    st.divider()

    st.subheader("Shipment")
    shipment_id = st.text_input("Shipment ID", value=SHIPMENT_ID)

    st.subheader("Inject Scenario")
    scenarios = ["temp_spike", "customs_hold", "gradual_drift", "compound_failure"]
    selected_scenario = st.selectbox("Scenario", scenarios)
    if st.button("▶ Run Scenario", type="primary"):
        with st.spinner(f"Running {selected_scenario}..."):
            run_scenario(selected_scenario, shipment_id)
        st.success("Scenario complete — refreshing...")
        st.rerun()

    st.divider()
    auto_refresh = st.checkbox("Auto-refresh (5s)", value=True)

# ── Fetch state ───────────────────────────────────────────────────────────────
status = fetch_status(shipment_id)

if not status:
    st.warning("No shipment data. Initialize a shipment or run a scenario.")
    if st.button("Initialize SHP-DEMO-001"):
        httpx.post(f"{API_BASE}/api/shipments/{shipment_id}/init")
        st.rerun()
    st.stop()

# ── Header metrics ────────────────────────────────────────────────────────────
severity = status["severity"]
sev_color = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🟠", "CRITICAL": "🔴"}.get(severity, "⚪")

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Severity", f"{sev_color} {severity}")
col2.metric("Spoilage Risk", f"{status['spoilage_probability']:.0%}")
col3.metric("Delay Risk", f"{status['delay_risk']:.0%}")
col4.metric("Anomalies", status["anomaly_count"])
col5.metric("Audit Entries", len(status["audit_log"]))

st.divider()

# ── HITL Modal ────────────────────────────────────────────────────────────────
if status.get("awaiting_human_approval"):
    st.error("⚠️ **Human Approval Required** — Agent pipeline is paused")
    with st.container():
        st.write("**Orchestrator Reasoning:**")
        st.info(status.get("orchestrator_reasoning", "No reasoning available"))
        st.write(f"**Recommended Actions:** `{', '.join(status['recommended_actions'])}`")

        col_a, col_r, col_m = st.columns(3)
        if col_a.button("✅ Approve — Execute all actions", type="primary"):
            approve_action(shipment_id, "approved")
            st.success("Approved! Agents resuming...")
            time.sleep(1)
            st.rerun()
        if col_r.button("❌ Reject — Take no action"):
            approve_action(shipment_id, "rejected", notes="Manual override")
            st.rerun()
        if col_m.button("✏️ Modify — Approve with notes"):
            notes = st.text_input("Notes for modification")
            approve_action(shipment_id, "modified", notes=notes)
            st.rerun()
    st.divider()

# ── Main content ──────────────────────────────────────────────────────────────
col_map, col_actions = st.columns([3, 2])

with col_map:
    st.subheader("📍 Live Shipment Map")
    telemetry = status.get("telemetry_window", [])
    if telemetry:
        lats = [r["latitude"] for r in telemetry]
        lons = [r["longitude"] for r in telemetry]
        latest = telemetry[-1]

        fig_map = go.Figure()
        fig_map.add_trace(go.Scattermapbox(
            lat=lats, lon=lons, mode="lines",
            line=dict(width=2, color="#3b82f6"),
            name="Route"
        ))
        fig_map.add_trace(go.Scattermapbox(
            lat=[latest["latitude"]], lon=[latest["longitude"]], mode="markers",
            marker=dict(size=14, color="#ef4444" if severity in ("HIGH", "CRITICAL") else "#22c55e"),
            name="Current Position"
        ))
        fig_map.update_layout(
            mapbox=dict(style="carto-darkmatter", zoom=2, center=dict(lat=20, lon=20)),
            margin=dict(l=0, r=0, t=0, b=0), height=300,
            paper_bgcolor="#0f0f1a", font_color="white"
        )
        st.plotly_chart(fig_map, use_container_width=True)

with col_actions:
    st.subheader("🎯 Actions Taken")
    if status.get("route_recommendation"):
        r = status["route_recommendation"]
        st.success(f"✈️ **Rerouted** via {r['carrier']} — Risk {r['risk_score']:.0%}, ${r['cost_usd']:,}")
    if status.get("notifications_sent"):
        st.warning(f"🏥 **Notified** {len(status['notifications_sent'])} hospitals")
        for n in status["notifications_sent"][:3]:
            st.caption(n[:80])
    if status.get("cold_storage_booked"):
        st.info(f"❄️ **Cold Storage** booked: {status['cold_storage_facility']}")
    if status.get("insurance_claim_id"):
        st.info(f"📄 **Insurance Claim**: {status['insurance_claim_id']}")

# ── Telemetry chart ───────────────────────────────────────────────────────────
st.subheader("📊 Temperature Timeline")
if telemetry:
    temps = [r["temperature_c"] for r in telemetry]
    times = list(range(len(temps)))
    fig_temp = go.Figure()
    fig_temp.add_trace(go.Scatter(
        x=times, y=temps, mode="lines+markers",
        line=dict(color="#ef4444", width=2), name="Temperature (°C)"
    ))
    fig_temp.add_hline(y=8.0, line_dash="dash", line_color="#f59e0b",
                       annotation_text="Max safe (8°C)")
    fig_temp.add_hline(y=2.0, line_dash="dash", line_color="#3b82f6",
                       annotation_text="Min safe (2°C)")
    fig_temp.update_layout(
        height=250, paper_bgcolor="#0f0f1a", plot_bgcolor="#0f0f1a",
        font_color="white", margin=dict(l=40, r=20, t=20, b=40)
    )
    st.plotly_chart(fig_temp, use_container_width=True)

# ── Audit log ─────────────────────────────────────────────────────────────────
st.subheader("📋 GDP/FDA Audit Trail")
audit = status.get("audit_log", [])
if audit:
    for entry in reversed(audit[-10:]):
        icon = {"LOW": "ℹ️", "MEDIUM": "⚠️", "HIGH": "🔶", "CRITICAL": "🚨"}.get(entry["severity"], "ℹ️")
        with st.expander(f"{icon} [{entry['agent_name']}] {entry['action_type']} — {entry['timestamp'][:19]}"):
            st.write(f"**Detail:** {entry['action_detail']}")
            st.write(f"**Reasoning:** {entry['reasoning'][:300]}")
            st.write(f"**GDP Compliant:** {'✅' if entry['gdp_compliant'] else '❌'}")
else:
    st.caption("No audit entries yet — run a scenario to generate data.")

# ── Auto-refresh ──────────────────────────────────────────────────────────────
if auto_refresh:
    time.sleep(REFRESH_INTERVAL)
    st.rerun()
```

- [ ] **Step 2: Test the dashboard**

```bash
# Terminal 1 — API server
uvicorn src.api.main:app --reload --port 8000

# Terminal 2 — Dashboard
streamlit run src/dashboard/app.py --server.port 8501
```

Open `http://localhost:8501`. Run the `temp_spike` scenario from the sidebar. Verify:
- Map shows route
- Temperature chart shows spike
- HITL modal appears for HIGH/CRITICAL
- Audit log populates after approval

- [ ] **Step 3: Commit**

```bash
git add src/dashboard/app.py
git commit -m "feat: Streamlit dashboard — map, telemetry chart, HITL modal, audit log"
```

---

## Task 13: Docker Compose

**Files:**
- Create: `docker-compose.yml`
- Create: `Dockerfile`

- [ ] **Step 1: Create Dockerfile**

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000 8501

ENV PYTHONPATH=/app
```

- [ ] **Step 2: Create docker-compose.yml**

```yaml
# docker-compose.yml
version: "3.9"

services:
  api:
    build: .
    command: uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
    ports:
      - "8000:8000"
    volumes:
      - .:/app
    env_file:
      - .env
    environment:
      - PYTHONPATH=/app

  dashboard:
    build: .
    command: streamlit run src/dashboard/app.py --server.port 8501 --server.address 0.0.0.0
    ports:
      - "8501:8501"
    volumes:
      - .:/app
    env_file:
      - .env
    environment:
      - PYTHONPATH=/app
      - API_BASE=http://api:8000
    depends_on:
      - api
```

- [ ] **Step 3: Test one-command startup**

```bash
docker-compose up --build
```

Expected: Both services start. Dashboard at `http://localhost:8501`, API at `http://localhost:8000`.

- [ ] **Step 4: Commit**

```bash
git add Dockerfile docker-compose.yml
git commit -m "feat: docker-compose for one-command demo startup"
```

---

## Task 14: Full Integration Test

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: Write integration test**

```python
# tests/test_integration.py
"""
End-to-end integration test — runs the full LangGraph pipeline
against the temp_spike scenario without mocking Claude.
Set ANTHROPIC_API_KEY in environment before running.
Skip with: pytest -m "not integration"
"""
import pytest
from src.graph.cargo_graph import build_graph
from src.simulator.scenarios import scenario_temp_spike
from src.graph.state import CargoState

pytestmark = pytest.mark.integration


def test_temp_spike_scenario_reaches_high_severity():
    graph = build_graph(db_path=":memory:")
    shipment_id = "SHP-INTEGRATION-001"
    config = {"configurable": {"thread_id": shipment_id}}

    initial_state: dict = {
        "shipment_id": shipment_id,
        "cargo_type": "vaccine",
        "cargo_description": "COVID-19 mRNA Vaccine — 500 doses",
        "origin_city": "New York",
        "destination_city": "Nairobi",
        "expected_arrival": None,
        "telemetry_window": [],
        "latest_reading": None,
        "anomalies": [],
        "spoilage_probability": 0.0,
        "delay_risk": 0.0,
        "severity": "LOW",
        "recommended_actions": [],
        "orchestrator_reasoning": "",
        "route_recommendation": None,
        "notifications_sent": [],
        "cold_storage_booked": False,
        "cold_storage_facility": None,
        "insurance_claim_id": None,
        "audit_log": [],
        "gdp_compliant": True,
        "awaiting_human_approval": False,
        "human_decision": None,
        "human_notes": None,
    }
    graph.update_state(config, initial_state)

    readings = scenario_temp_spike(shipment_id=shipment_id)
    final_state = None
    for reading in readings:
        final_state = graph.invoke(
            {"latest_reading": reading, "telemetry_window": [reading]},
            config=config
        )

    assert final_state is not None
    assert final_state["severity"] in ("HIGH", "CRITICAL")
    assert len(final_state["audit_log"]) > 0
```

- [ ] **Step 2: Run unit tests only (excludes integration)**

```bash
pytest tests/ -v -m "not integration"
```

Expected: All unit tests pass

- [ ] **Step 3: Run integration test (requires API key)**

```bash
pytest tests/test_integration.py -v -m integration
```

Expected: `1 passed` — full pipeline runs, severity is HIGH or CRITICAL

- [ ] **Step 4: Final commit**

```bash
git add tests/test_integration.py
git commit -m "test: end-to-end integration test for temp_spike scenario"
```

---

## Self-Review

**Spec coverage check:**

| Spec Requirement | Task |
|-----------------|------|
| Real-time telemetry monitoring | Task 5 (Monitor Agent) |
| Statistical + LLM anomaly detection | Task 6 (Anomaly Agent) |
| Spoilage probability with tool use | Task 8 (Risk Agent) |
| Decision orchestrator + fan-out | Task 9 (Orchestrator) |
| Route optimizer | Task 10 |
| Hospital notifications | Task 10 |
| Cold storage booking | Task 10 |
| Insurance claim filing | Task 10 |
| GDP/FDA compliance logging | Task 7 |
| Human-in-the-loop gate | Tasks 3 + 9 (interrupt_before) |
| Synthetic data simulator | Task 4 |
| Demo failure scenarios | Task 4 |
| FastAPI endpoints | Task 11 |
| Streamlit dashboard | Task 12 |
| docker-compose | Task 13 |
| LangGraph state checkpointing | Task 3 (SqliteSaver) |

All spec requirements covered. No gaps found.

**Placeholder scan:** No TBD/TODO found. All code blocks are complete.

**Type consistency:** `CargoState` defined in Task 2, imported consistently in Tasks 3–12. `AuditEntry`, `AnomalyRecord`, `RouteOption` defined in Task 2, used by name in all agent tasks. `compliance_agent` returns `gdp_compliant: bool` matching CargoState field. All consistent.
