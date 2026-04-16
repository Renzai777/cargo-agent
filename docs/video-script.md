# AI Cargo Monitor — 5-Minute Video Script & Production Doc
**UMD Agentic AI Hackathon 2026 · Case 6**

---

## Production Notes

| Item | Detail |
|------|--------|
| Total runtime | 5:00 (±15 seconds) |
| Word count | ~720 words at 145 wpm |
| Visual style | Screen recording + diagram overlays |
| Narration | Single speaker, conversational tone |
| Background music | Ambient/low-key (optional, 30% volume) |

---

## Scene-by-Scene Breakdown

| # | Scene | Duration | Visual |
|---|-------|----------|--------|
| 1 | Hook — The Problem | 0:00–0:35 | B-roll: airplane cargo hold, news headline mock-up |
| 2 | Solution Intro | 0:35–1:10 | Dashboard overview screenshot |
| 3 | Architecture Overview | 1:10–2:00 | Animated agent pipeline diagram |
| 4 | Live Demo — Temp Spike Scenario | 2:00–3:20 | Live screen recording of dashboard |
| 5 | Human-in-the-Loop | 3:20–3:50 | Screen recording — HITL approval modal |
| 6 | Tech Stack & Design Choices | 3:50–4:30 | Diagram: LangGraph + Claude + FastAPI |
| 7 | Closing — Impact | 4:30–5:00 | Final dashboard shot + credits |

---

## Full Narration Transcript

---

### SCENE 1 — THE PROBLEM (0:00 – 0:35)

> *[Show: cargo plane image, then a flashing temperature alert graphic]*

Imagine a shipment of 10,000 vaccine doses flying from New York to Nairobi.
Somewhere over the Atlantic, the refrigeration unit fails.

The temperature inside the container starts climbing.

In the current system, nobody knows — until it's too late. By the time a human
notices, the vaccines are spoiled. Hospitals have no stock. Patients miss their
scheduled appointments.

This is a real problem in pharmaceutical cold-chain logistics. And this is what
we built AI Cargo Monitor to solve.

---

### SCENE 2 — SOLUTION INTRO (0:35 – 1:10)

> *[Show: Streamlit dashboard — main view with live map and metrics]*

AI Cargo Monitor is an autonomous multi-agent AI system that watches every
sensor reading from a smart cargo container in real time — and acts before
damage occurs.

It ingests telemetry every 30 seconds: temperature, humidity, shock levels,
GPS position, and customs status.

When something goes wrong, a cascade of specialized AI agents kicks in
automatically — detecting the anomaly, assessing the risk, recommending
interventions, and coordinating everything from rerouting the shipment to
notifying hospitals — all within seconds.

And for high-stakes decisions, it keeps a human in the loop.

---

### SCENE 3 — ARCHITECTURE OVERVIEW (1:10 – 2:00)

> *[Show: animated pipeline diagram — agents lighting up sequentially]*

The system is built on LangGraph — a framework for stateful, multi-agent
pipelines.

Here's how the agent pipeline works:

First, the **Monitor Agent** receives each telemetry reading and checks it
against GDP cold-chain thresholds — safe range for vaccines is 2 to 8 degrees
Celsius.

If a breach is detected, the **Anomaly Detection Agent** runs both statistical
analysis — using Z-scores — and sends the pattern to Claude for contextual
reasoning. "Is this a sudden spike or a gradual drift? How serious is it?"

The **Risk Assessment Agent** then uses Claude with structured tool calls to
calculate spoilage probability and factor in the remaining route time.

Based on severity, the **Decision Orchestrator** fans out to up to five
parallel action agents simultaneously: Route Optimizer, Notification Agent,
Cold Storage booking, Insurance Claim filing, and the Compliance Logger —
which writes an immutable audit trail in FDA 21 CFR Part 11 format.

---

### SCENE 4 — LIVE DEMO (2:00 – 3:20)

> *[Show: screen recording — click "Run Live" on Temp Spike scenario]*

Let's see it in action. We'll trigger the temperature spike scenario — this
simulates a refrigeration failure two hours into a flight.

Watch the live map. The cargo dot turns red as the temperature climbs past the
8-degree threshold.

On the left sidebar, you can see the agent pipeline lighting up in sequence —
Monitor fires, Anomaly Detector flags a critical breach, Risk Assessor
calculates a 78% spoilage probability.

The sensor timeline shows the temperature chart spiking in real time, with AI
forecast projecting the trajectory forward.

The system severity jumps to CRITICAL.

Now the Decision Orchestrator has built its reasoning — you can see it in the
audit trail — weighing spoilage risk, intervention cost, regulatory obligation
under GDP Article 9.2, and patient impact downstream.

It recommends four actions: reroute, notify hospitals, book cold storage, and
file an insurance claim.

But before executing, it pauses.

---

### SCENE 5 — HUMAN IN THE LOOP (3:20 – 3:50)

> *[Show: HITL approval modal lighting up in red]*

This is the Human-in-the-Loop gate.

The orchestrator surfaces its full reasoning and recommended actions to the
operator. They can approve, reject, or modify with notes.

We click Approve.

And instantly — all five cascading actions execute in parallel. The route
optimizer books an alternative carrier. Hospitals are notified. Cold storage
is reserved at Frankfurt. An insurance claim is opened. Every single step is
logged in the audit trail.

This is agentic AI working the way it should — autonomous where it can be,
accountable where it must be.

---

### SCENE 6 — TECH STACK (3:50 – 4:30)

> *[Show: tech stack diagram — boxes for each component]*

A quick look under the hood:

We used **LangGraph** for stateful agent orchestration — with built-in
checkpointing so no state is ever lost, and native interrupt support for the
HITL gate.

**Claude Sonnet** from Anthropic powers the reasoning agents — anomaly
classification, risk scoring, and orchestration decisions — with structured
tool use for calling simulated external APIs.

**FastAPI** handles the backend — telemetry ingestion, state queries, HITL
approval, and a Server-Sent Events stream for real-time dashboard updates.

**Streamlit** with Plotly renders the live dashboard — the map, sensor
timelines, agent pipeline view, and the approval modal — all refreshing every
5 seconds.

All telemetry data is synthetic, generated by a scenario simulator that can
inject failures — temperature spikes, customs holds, compound failures — on
demand.

---

### SCENE 7 — CLOSING (4:30 – 5:00)

> *[Show: final dashboard — completed scenario, all 5 actions triggered, full audit log]*

AI Cargo Monitor demonstrates what a purpose-built agentic AI system can look
like in a high-stakes logistics domain.

Autonomous detection. Cascading coordination. Regulatory compliance baked in.
And a human who stays in control of the decisions that matter most.

Built for the UMD Agentic AI Hackathon 2026.

Thank you.

---

## Key Talking Points Cheat Sheet

| Theme | Key Phrase |
|-------|-----------|
| Problem | "Spoiled vaccines. Patients without stock. No one knew in time." |
| Uniqueness | "Not just monitoring — autonomous cascading action" |
| HITL | "Autonomous where it can be, accountable where it must be" |
| LangGraph | "Stateful, checkpointed, native interrupt support" |
| Claude | "Contextual reasoning + structured tool use" |
| Compliance | "21 CFR Part 11 — immutable, timestamped, per-agent audit trail" |
| Scale | "Five parallel action agents triggered from one risk event" |

---

## On-Screen Text Cues (for captions/overlays)

| Timestamp | Text |
|-----------|------|
| 0:05 | "10,000 vaccine doses. One refrigeration failure." |
| 0:35 | "AI Cargo Monitor — Autonomous Cold-Chain Response" |
| 1:10 | "9 Specialized Agents · LangGraph Pipeline" |
| 1:18 | "Monitor Agent → GDP threshold check" |
| 1:28 | "Anomaly Detector → Z-score + Claude reasoning" |
| 1:40 | "Risk Assessor → Spoilage probability via tool use" |
| 1:50 | "Decision Orchestrator → Fan-out to 5 action agents" |
| 2:00 | "DEMO: Temp Spike Scenario" |
| 2:45 | "Spoilage probability: 78%" |
| 3:20 | "Human-in-the-Loop Gate" |
| 3:38 | "5 Cascading Actions — Executing in Parallel" |
| 3:50 | "Stack: LangGraph · Claude Sonnet · FastAPI · Streamlit" |
| 4:30 | "Audit Trail: FDA 21 CFR Part 11 Compliant" |
| 4:50 | "UMD Agentic AI Hackathon 2026 · Case 6" |
