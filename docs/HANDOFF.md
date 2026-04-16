# AI Cargo Monitor — Session Handoff Doc
**Date:** 2026-04-16
**Project:** UMD Agentic AI Hackathon 2026 — Case 6: AI Cargo Monitor
**Project Root:** `C:\Users\A0099934\Pictures\AgenticAI`
**Deadline:** April 24 (final presentation)

---

## What We Are Building

A LangGraph multi-agent Python system that monitors pharmaceutical cold-chain shipments in real time. When sensor anomalies are detected, a pipeline of AI agents detects the risk, decides on interventions, and executes cascading actions (rerouting, hospital notifications, insurance claims, compliance logging) — with a human-in-the-loop approval gate.

**Demo scenario:** Vaccine shipment NYC → Frankfurt → Nairobi. Temperature spikes mid-flight. System detects, classifies CRITICAL, pauses for human approval, then fires 5 parallel actions: reroute cargo, notify hospitals, book cold storage, file insurance claim, write GDP audit log.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent framework | LangGraph 0.2+ |
| LLM | Claude claude-sonnet-4-6 (`claude-sonnet-4-6`) via Anthropic SDK |
| API | FastAPI + Uvicorn |
| Dashboard | Streamlit + Plotly |
| State store | SQLite via LangGraph SqliteSaver |
| Data models | Pydantic v2 |
| Data generation | Synthetic (numpy + scripted scenarios) |
| Testing | pytest + pytest-asyncio |
| Runtime | Python 3.13 venv at `venv/` |

---

## Key Design Decisions

- **Architecture:** Option A — LangGraph State Machine (not CrewAI, not custom orchestrator)
- **HITL gate:** `interrupt_before=["decision_orchestrator"]` — pauses before high-stakes decisions
- **Fan-out:** `Send` API in `_route_orchestrator()` — parallel action agents from single orchestrator
- **State:** `CargoState` TypedDict with `Annotated[list, operator.add]` for append-only fields
- **Data:** All synthetic — `TelemetrySimulator` class + 4 scenario scripts

---

## Docs Written (All in `docs/`)

| Doc | Location |
|-----|---------|
| Architecture | `docs/architecture/system-architecture.md` |
| High Level Design | `docs/high-level-design/HLD.md` |
| Low Level Design | `docs/low-level-design/LLD.md` |
| Research / cold-chain refs | `docs/research/cold-chain-references.md` |
| Master design spec | `docs/superpowers/specs/2026-04-16-ai-cargo-monitor-design.md` |
| **Implementation plan** | `docs/superpowers/plans/2026-04-16-ai-cargo-monitor.md` ← READ THIS FIRST |

---

## File Structure To Build

```
C:\Users\A0099934\Pictures\AgenticAI\
├── venv/                          ✅ EXISTS — Python 3.13 venv
├── src/
│   ├── graph/
│   │   ├── state.py               ❌ TODO Task 2
│   │   └── cargo_graph.py         ❌ TODO Task 3
│   ├── agents/
│   │   ├── monitor.py             ❌ TODO Task 5
│   │   ├── anomaly_detector.py    ❌ TODO Task 6
│   │   ├── risk_assessor.py       ❌ TODO Task 8
│   │   ├── orchestrator.py        ❌ TODO Task 9
│   │   ├── route_optimizer.py     ❌ TODO Task 10
│   │   ├── notification.py        ❌ TODO Task 10
│   │   ├── cold_storage.py        ❌ TODO Task 10
│   │   ├── insurance.py           ❌ TODO Task 10
│   │   └── compliance.py          ❌ TODO Task 7
│   ├── tools/
│   │   ├── spoilage.py            ❌ TODO Task 8
│   │   ├── routing.py             ❌ TODO Task 8
│   │   ├── notifications.py       ❌ TODO Task 9
│   │   ├── storage.py             ❌ TODO Task 9
│   │   ├── claims.py              ❌ TODO Task 9
│   │   └── compliance_rules.py    ❌ TODO Task 7
│   ├── simulator/
│   │   ├── telemetry.py           ❌ TODO Task 4
│   │   └── scenarios.py           ❌ TODO Task 4
│   ├── api/
│   │   └── main.py                ❌ TODO Task 11
│   └── dashboard/
│       └── app.py                 ❌ TODO Task 12
├── tests/
│   ├── conftest.py                ✅ EXISTS (needs minor fix — see below)
│   ├── test_models.py             ❌ TODO Task 2
│   ├── test_graph.py              ❌ TODO Task 3
│   ├── test_simulator.py          ❌ TODO Task 4
│   ├── test_monitor.py            ❌ TODO Task 5
│   ├── test_anomaly.py            ❌ TODO Task 6
│   ├── test_action_agents.py      ❌ TODO Tasks 7 + 10
│   ├── test_risk.py               ❌ TODO Task 8
│   ├── test_orchestrator.py       ❌ TODO Task 9
│   └── test_integration.py        ❌ TODO Task 14
├── data/synthetic/                ✅ EXISTS (empty)
├── docs/                          ✅ EXISTS (all design docs)
├── requirements.txt               ✅ EXISTS
├── .env.example                   ✅ EXISTS (needs 1-line fix — see below)
├── .env                           ✅ EXISTS (copy of .env.example — add real API key)
├── .gitignore                     ✅ EXISTS
├── pytest.ini                     ✅ EXISTS
├── Dockerfile                     ❌ TODO Task 13
└── docker-compose.yml             ❌ TODO Task 13
```

---

## Current Status of All 14 Tasks

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Project setup — venv, folders, deps, conftest | ✅ DONE (needs minor fixes) | See fixes below |
| 2 | Pydantic data models + CargoState | ❌ TODO | |
| 3 | LangGraph graph skeleton | ❌ TODO | Depends on Task 2 |
| 4 | Telemetry simulator + scenarios | ❌ TODO | Depends on Task 2 |
| 5 | Monitor Agent | ❌ TODO | Depends on Tasks 2, 3, 4 |
| 6 | Anomaly Detection Agent | ❌ TODO | Depends on Tasks 2, 3 — calls Claude |
| 7 | Compliance Agent + GDP tools | ❌ TODO | Depends on Tasks 2, 3 |
| 8 | Risk Assessment Agent | ❌ TODO | Depends on Tasks 2, 3 — calls Claude with tool use |
| 9 | Decision Orchestrator Agent | ❌ TODO | Depends on Tasks 2, 3 — calls Claude with tool use |
| 10 | Route / Notification / Cold Storage / Insurance agents | ❌ TODO | Depends on Tasks 2, 3, 9 |
| 11 | FastAPI backend | ❌ TODO | Depends on Tasks 2–10 |
| 12 | Streamlit dashboard | ❌ TODO | Depends on Task 11 |
| 13 | docker-compose | ❌ TODO | Depends on Tasks 11, 12 |
| 14 | End-to-end integration test | ❌ TODO | Depends on all above |

---

## Pending Fixes for Task 1 (Apply Before Starting Task 2)

### Fix 1 — `.env.example` line 1
Change:
```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```
To:
```
ANTHROPIC_API_KEY=your-anthropic-api-key-here
```

### Fix 2 — `tests/conftest.py`
Remove the redundant `from datetime import datetime` inside `base_state` fixture (line ~42). Keep the top-level import at line 2.

### Fix 3 — `pytest.ini`
Add marker declarations:
```ini
markers =
    unit: fast isolated unit tests
    integration: tests that touch I/O or external services
```

### Fix 4 — `.gitignore`
Append:
```
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/
data/synthetic/
.DS_Store
Thumbs.db
*.sqlite3
```

### Commit message for fixes:
```
fix: scaffold quality — safe API key placeholder, conftest cleanup, gitignore, pytest markers
```

---

## How to Run Everything (Once Built)

### Activate venv (Windows)
```bash
cd "C:\Users\A0099934\Pictures\AgenticAI"
venv\Scripts\activate
```

### Set your real API key
Edit `.env`:
```
ANTHROPIC_API_KEY=sk-ant-...your real key...
```

### Run tests
```bash
venv\Scripts\pytest tests/ -v -m "not integration"
```

### Run integration test (calls real Claude API)
```bash
venv\Scripts\pytest tests/test_integration.py -v -m integration
```

### Start API server
```bash
venv\Scripts\uvicorn src.api.main:app --reload --port 8000
```

### Start dashboard
```bash
venv\Scripts\streamlit run src/dashboard/app.py --server.port 8501
```

### One-command start (after Docker built)
```bash
docker-compose up --build
```

---

## Full Code for Every File (In the Plan)

The complete implementation plan with full code for every file is at:
```
docs/superpowers/plans/2026-04-16-ai-cargo-monitor.md
```

This file contains:
- Exact code for every agent, tool, graph, simulator, API, dashboard
- TDD steps (write failing test → implement → run → pass → commit)
- Exact pytest commands and expected outputs
- Git commit messages for each task

**To resume in a new session:** Tell Claude to read `docs/superpowers/plans/2026-04-16-ai-cargo-monitor.md` and `docs/HANDOFF.md`, apply the Task 1 fixes, then execute Tasks 2–14 using the subagent-driven-development skill.

---

## Key Code Snippets to Know

### CargoState shape (Task 2)
The central state object passed between all LangGraph nodes:
```python
class CargoState(TypedDict):
    shipment_id: str
    cargo_type: str          # "vaccine" | "biologics"
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    spoilage_probability: float   # 0.0–1.0
    anomalies: Annotated[list[AnomalyRecord], operator.add]
    audit_log: Annotated[list[AuditEntry], operator.add]
    recommended_actions: list[str]   # ["REROUTE", "NOTIFY_HOSPITALS", ...]
    awaiting_human_approval: bool
    # ... + 15 more fields
```

### LangGraph graph flow (Task 3)
```
START → monitor_agent → anomaly_agent → risk_agent
  → (severity LOW) → compliance_agent → END
  → (severity HIGH/CRITICAL) → [HITL interrupt] → decision_orchestrator
      → Send("route_optimizer") + Send("notification_agent") + Send("cold_storage_agent")
        + Send("insurance_agent") + Send("compliance_agent")  [parallel]
      → all → END
```

### HITL interrupt pattern (Task 3)
```python
graph.compile(
    checkpointer=SqliteSaver(conn),
    interrupt_before=["decision_orchestrator"]
)
# Resume after human approves via /api/shipments/{id}/approve
graph.invoke(None, config=config)
```

### Demo scenarios available (Task 4)
```python
from src.simulator.scenarios import SCENARIOS
SCENARIOS.keys()  # temp_spike, customs_hold, gradual_drift, compound_failure
```

---

## Git Log (Start of Next Session)
```bash
git log --oneline
# f18d9e8 feat: project scaffold — venv, folder structure, deps, conftest
```

---

## Important Notes

1. **Python version:** venv uses Python 3.13 (not 3.11 as originally planned — all packages work fine)
2. **All Claude calls use:** `model="claude-sonnet-4-6"` (claude-sonnet-4-6)
3. **venv commands on Windows:** use `venv\Scripts\python`, `venv\Scripts\pip`, `venv\Scripts\pytest` (NOT `python`/`pip`/`pytest` directly unless venv is activated)
4. **PYTHONPATH:** `pytest.ini` sets `pythonpath = .` so `from src.graph.state import ...` works without install
5. **No real API calls in unit tests** — all Claude calls mocked with `unittest.mock.patch`
6. **Integration tests** are marked `@pytest.mark.integration` and skipped by default
7. **Synthetic data only** — no real IoT, routing, hospital, or insurance APIs

---

## Sprint Plan (April 16–24)

| Date | Tasks | Goal |
|------|-------|------|
| Apr 16 | 1 (done), 2, 3 | Data models + graph skeleton working |
| Apr 17 | 4, 5 | Simulator + Monitor agent tested |
| Apr 18 | 6, 7 | Anomaly + Compliance agents tested |
| Apr 19 | 8, 9 | Risk + Orchestrator agents tested |
| Apr 20 | 10 | All 4 action agents tested |
| Apr 21 | 11, 12 | API + Dashboard running end-to-end |
| Apr 22 | 13, 14 | Docker + integration test |
| Apr 23 | — | Demo video recording + PDF writeup |
| Apr 24 | — | Final presentation |
