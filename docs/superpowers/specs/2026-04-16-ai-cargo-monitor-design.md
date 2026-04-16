# Design Spec — AI Cargo Monitor
**Date:** 2026-04-16
**Hackathon:** UMD Agentic AI Challenge 2026 · Case 6
**Team:** TBD
**Stack:** Python 3.11 · LangGraph · Claude claude-sonnet-4-6 · FastAPI · Streamlit

---

## Decision Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Agent framework | LangGraph | Stateful graph, native HITL, streaming, checkpoint |
| LLM | Claude claude-sonnet-4-6 | Best tool use + reasoning for multi-variable trade-offs |
| Dashboard | Streamlit | Pure Python, real-time, demo-ready fast |
| Data | Synthetic (numpy + Claude) | No real dataset available; inject failure scenarios |
| Architecture | Option A — LangGraph State Machine | Confirmed by team |

---

## What We're Building

A multi-agent AI system that monitors pharmaceutical cold-chain shipments in real time. When sensor anomalies are detected, a pipeline of specialized agents analyses the risk, decides on interventions, and coordinates cascading actions (rerouting, hospital notifications, insurance claims, compliance logging) — with a human approval gate for high-stakes decisions.

**The demo scenario:** A vaccine shipment from New York → Frankfurt → Nairobi. At the 2-hour mark, a refrigeration failure causes temperature to spike from 4.5°C to 16°C. The system detects it, classifies it CRITICAL, presents a HITL decision, and upon approval: reroutes the cargo, notifies 3 hospitals, books emergency cold storage, and files an insurance claim — all within 90 seconds.

---

## Architecture Summary

4-layer LangGraph pipeline:
1. **Data Layer** — Synthetic telemetry simulator + mocked external feeds
2. **Detection Layer** — Monitor Agent → Anomaly Agent → Risk Assessment Agent (sequential nodes)
3. **Decision Layer** — Decision Orchestrator Agent (fan-out via conditional_edges + Send API)
4. **Action Layer** — Route Optimizer, Notification, Cold Storage, Insurance, Compliance (parallel nodes)

Human-in-the-loop via LangGraph `interrupt_before` on Decision Orchestrator for HIGH/CRITICAL severity.

Full spec: see `docs/architecture/system-architecture.md`

---

## Folder Structure

```
ai-cargo-monitor/
├── src/agents/          # 9 agent files
├── src/graph/           # LangGraph definition + CargoState
├── src/simulator/       # Telemetry generator + scenarios
├── src/api/             # FastAPI
├── src/dashboard/       # Streamlit
├── src/tools/           # LangGraph tool definitions
├── data/synthetic/      # Pre-baked scenario data
├── tests/
├── docs/                # This folder
├── docker-compose.yml
└── requirements.txt
```

---

## Demo Script (5-min video)

| Time | What happens on screen |
|------|----------------------|
| 0:00–0:30 | Intro card + problem statement (text overlay) |
| 0:30–1:00 | Dashboard loads, normal shipment streaming, map shows NYC→Frankfurt route |
| 1:00–1:30 | Temperature spike injected — red alert fires on dashboard |
| 1:30–2:30 | Agent pipeline executes: Monitor → Anomaly → Risk — show reasoning in sidebar |
| 2:30–3:00 | HITL modal appears — show orchestrator reasoning chain, click Approve |
| 3:00–4:00 | Cascading actions fire in parallel: route changed on map, hospital notifications, insurance claim ID generated |
| 4:00–4:30 | Audit log shown — full GDP/FDA-compliant trail |
| 4:30–5:00 | Summary card: what the system did, why, time taken |

---

## Build Sprint Plan (April 16–24)

| Day | Milestone |
|-----|-----------|
| Apr 16 | Repo setup, CargoState, LangGraph graph skeleton, simulator working |
| Apr 17 | Monitor + Anomaly agents complete + tested |
| Apr 18 | Risk Agent + Orchestrator complete + tested |
| Apr 19 | All 5 action agents complete |
| Apr 20 | FastAPI layer + HITL approval endpoint |
| Apr 21 | Streamlit dashboard — map, charts, HITL modal |
| Apr 22 | End-to-end demo scenario working |
| Apr 23 | Demo video recording + PDF writeup |
| Apr 24 | Final presentation |

---

## Novelty Points (for judges)

1. **LangGraph `interrupt_before` HITL** — not just a chatbot, a true interruptible workflow
2. **LangGraph `Send` API fan-out** — parallel action agents coordinated through shared state
3. **Cascading consequence chain** — single anomaly triggers 5 downstream agents
4. **Compound failure scenario** — `scenario_multi_failure.py` shows temp + delay simultaneously
5. **FDA 21 CFR Part 11 audit trail** — every LLM reasoning chain is immutably logged
6. **Synthetic data injection API** — judges can trigger any failure scenario live during presentation
