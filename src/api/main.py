import json
import asyncio
from datetime import datetime
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.graph.cargo_graph import build_graph
from src.graph.state import TelemetryReading, HumanDecision, CargoState
from src.simulator.scenarios import SCENARIOS

app = FastAPI(
    title="AI Cargo Monitor",
    version="1.0.0",
    description="LangGraph multi-agent pharmaceutical cold-chain monitoring system",
)
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
    "inventory_impact": None,
    "audit_log": [],
    "gdp_compliant": True,
    "awaiting_human_approval": False,
    "human_decision": None,
    "human_notes": None,
    "orchestrator_thinking": None,
    "predicted_breach_minutes": None,
    "temperature_forecast": [],
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
    if not snapshot or not snapshot.values:
        raise HTTPException(status_code=404, detail="Shipment not found")
    values = snapshot.values
    return {
        "shipment_id": shipment_id,
        "severity": values.get("severity", "LOW"),
        "spoilage_probability": values.get("spoilage_probability", 0.0),
        "delay_risk": values.get("delay_risk", 0.0),
        "awaiting_human_approval": values.get("awaiting_human_approval", False),
        "orchestrator_reasoning": values.get("orchestrator_reasoning", ""),
        "orchestrator_thinking": values.get("orchestrator_thinking"),
        "recommended_actions": values.get("recommended_actions", []),
        "predicted_breach_minutes": values.get("predicted_breach_minutes"),
        "temperature_forecast": values.get("temperature_forecast", []),
        "anomaly_count": len(values.get("anomalies", [])),
        "anomalies": [a.model_dump() for a in values.get("anomalies", [])],
        "notifications_sent": values.get("notifications_sent", []),
        "cold_storage_booked": values.get("cold_storage_booked", False),
        "cold_storage_facility": values.get("cold_storage_facility"),
        "insurance_claim_id": values.get("insurance_claim_id"),
        "inventory_impact": values.get("inventory_impact"),
        "gdp_compliant": values.get("gdp_compliant", True),
        "audit_log": [e.model_dump() for e in values.get("audit_log", [])],
        "telemetry_window": [r.model_dump() for r in values.get("telemetry_window", [])[-20:]],
        "latest_reading": values.get("latest_reading").model_dump() if values.get("latest_reading") else None,
        "route_recommendation": values.get("route_recommendation").model_dump() if values.get("route_recommendation") else None,
    }


@app.get("/api/shipments/{shipment_id}/audit")
def get_audit_log(shipment_id: str, limit: int = Query(default=50, le=200)):
    """Full GDP/FDA-compliant audit trail for a shipment (21 CFR Part 11)."""
    config = {"configurable": {"thread_id": shipment_id}}
    snapshot = graph.get_state(config)
    if not snapshot or not snapshot.values:
        raise HTTPException(status_code=404, detail="Shipment not found")
    values = snapshot.values
    audit = [e.model_dump() for e in values.get("audit_log", [])]
    return {
        "shipment_id": shipment_id,
        "total_entries": len(audit),
        "gdp_compliant": values.get("gdp_compliant", True),
        "audit_log": audit[-limit:],
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
    return {
        "status": "resumed",
        "severity": result.get("severity"),
        "actions": result.get("recommended_actions", []),
        "inventory_impact": result.get("inventory_impact"),
    }


@app.post("/api/scenarios/{scenario_name}/run/{shipment_id}")
async def run_scenario(scenario_name: str, shipment_id: str):
    if scenario_name not in SCENARIOS:
        raise HTTPException(
            status_code=404,
            detail=f"Scenario '{scenario_name}' not found. Available: {list(SCENARIOS)}"
        )
    readings = SCENARIOS[scenario_name](shipment_id=shipment_id)
    await init_shipment(shipment_id)
    results = []
    for reading in readings:
        r = await ingest_telemetry(shipment_id, reading)
        results.append(r)
    return {"scenario": scenario_name, "readings_processed": len(readings), "final_status": results[-1]}


@app.get("/api/scenarios")
def list_scenarios():
    return {"scenarios": list(SCENARIOS.keys()), "descriptions": {
        "temp_spike": "Refrigeration failure — temperature spikes to 16°C mid-flight",
        "customs_hold": "Shipment held at Frankfurt customs for 4+ hours",
        "gradual_drift": "Temperature slowly drifts above safe range over 20 readings",
        "compound_failure": "Temperature spike + customs hold simultaneously",
    }}


@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}
