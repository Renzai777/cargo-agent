import asyncio
import uuid
from datetime import datetime
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from src.runtime_config import load_runtime_env

load_runtime_env()

from src.graph.cargo_graph import build_graph
from src.graph.state import HumanDecision, TelemetryReading

app = FastAPI(
    title="AI Cargo Monitor",
    version="1.0.0",
    description="LangGraph multi-agent pharmaceutical cold-chain monitoring system",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

graph = build_graph()

_thread_map: dict[str, str] = {}
_scenario_runs: dict[str, dict] = {}
_scenario_tasks: dict[str, asyncio.Task] = {}
_APPROVAL_RESUME_NODES = {
    "decision_orchestrator",  # graph interrupts before this node — must be included
    "route_optimizer",
    "notification_agent",
    "inventory_agent",
    "cold_storage_agent",
    "insurance_agent",
    "compliance_agent",
}

DEFAULT_STATE: dict = {
    "cargo_type": "vaccine",
    "cargo_description": "COVID-19 mRNA Vaccine - 500 doses",
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


def _config(shipment_id: str) -> dict:
    thread_id = _thread_map.get(shipment_id, shipment_id)
    return {"configurable": {"thread_id": thread_id}}


def _obj_to_dict(obj) -> dict | None:
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, dict):
        return obj
    return None


def _list_to_dicts(items: list) -> list[dict]:
    return [d for item in items if (d := _obj_to_dict(item)) is not None]


def _isoformat(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _serialize_scenario_run(run: dict | None) -> dict | None:
    if not run:
        return None

    total = max(run.get("total_readings", 0), 1)
    processed = run.get("processed_readings", 0)
    return {
        "scenario_name": run.get("scenario_name"),
        "mode": run.get("mode"),
        "status": run.get("status"),
        "processed_readings": processed,
        "total_readings": run.get("total_readings", 0),
        "progress_pct": round(processed / total * 100, 1),
        "step_delay_ms": run.get("step_delay_ms", 0),
        "auto_approve_actions": run.get("auto_approve_actions", False),
        "started_at": _isoformat(run.get("started_at")),
        "updated_at": _isoformat(run.get("updated_at")),
        "completed_at": _isoformat(run.get("completed_at")),
        "last_error": run.get("last_error"),
        "last_result": run.get("last_result"),
    }


def _touch_run(run: dict):
    run["updated_at"] = datetime.utcnow()


async def _cancel_scenario_task(shipment_id: str, *, drop_run: bool = False):
    task = _scenario_tasks.pop(shipment_id, None)
    if task and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    if drop_run:
        _scenario_runs.pop(shipment_id, None)
        return

    run = _scenario_runs.get(shipment_id)
    if run and run.get("status") in {"running", "paused_for_approval"}:
        run["status"] = "cancelled"
        run["completed_at"] = datetime.utcnow()
        _touch_run(run)


async def _invoke_graph_update(shipment_id: str, update: dict) -> dict:
    config = _config(shipment_id)
    try:
        result = await asyncio.get_running_loop().run_in_executor(
            None, lambda: graph.invoke(update, config=config)
        ) or {}
        snapshot = graph.get_state(config)
        return {
            "status": "processed",
            "severity": result.get("severity", "LOW"),
            "awaiting_approval": result.get("awaiting_human_approval", False) or bool(snapshot and snapshot.next),
            "anomalies": len(result.get("anomalies", [])),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


async def _resume_graph_after_approval(shipment_id: str, notes: str = "") -> dict:
    config = _config(shipment_id)
    graph.update_state(config, {
        "human_decision": "approved",
        "human_notes": notes,
        "awaiting_human_approval": False,
    })
    return await asyncio.get_running_loop().run_in_executor(
        None, lambda: graph.invoke(None, config=config)
    ) or {}


def _is_anomalous(reading: TelemetryReading) -> bool:
    return (
        reading.temperature_c > 9.0
        or reading.temperature_c < 1.5
        or reading.humidity_pct > 78.0
        or reading.shock_g > 2.5
        or reading.customs_status == "held"
    )


async def _process_scenario_reading(shipment_id: str, reading: TelemetryReading) -> dict:
    config = _config(shipment_id)
    graph.update_state(config, {
        "latest_reading": reading,
        "telemetry_window": [reading],
    })

    last_result = {
        "status": "updated",
        "severity": "LOW",
        "awaiting_approval": False,
        "anomalies": 0,
    }

    if _is_anomalous(reading):
        try:
            last_result = await _invoke_graph_update(
                shipment_id,
                {"latest_reading": reading, "telemetry_window": []},
            )
        except HTTPException as exc:
            raise RuntimeError(str(exc.detail)) from exc

    return last_result


async def _execute_scenario_run(shipment_id: str) -> dict:
    run = _scenario_runs[shipment_id]
    last_result = run.get("last_result", {
        "status": "pending",
        "severity": "LOW",
        "awaiting_approval": False,
        "anomalies": 0,
    })

    try:
        while run["next_index"] < run["total_readings"]:
            run["status"] = "running"
            _touch_run(run)

            reading = run["readings"][run["next_index"]]
            last_result = await _process_scenario_reading(shipment_id, reading)

            run["next_index"] += 1
            run["processed_readings"] = run["next_index"]
            run["last_result"] = last_result
            _touch_run(run)

            if last_result.get("awaiting_approval"):
                if run.get("auto_approve_actions"):
                    resumed = await _resume_graph_after_approval(
                        shipment_id,
                        notes="Auto-approved during full scenario replay",
                    )
                    last_result = {
                        "status": "resumed",
                        "severity": resumed.get("severity", last_result.get("severity", "LOW")),
                        "awaiting_approval": False,
                        "anomalies": len(resumed.get("anomalies", [])),
                    }
                    run["last_result"] = last_result
                    _touch_run(run)
                    continue

                run["status"] = "paused_for_approval"
                _touch_run(run)
                return last_result

            if run["mode"] == "playback" and run["next_index"] < run["total_readings"]:
                await asyncio.sleep(run["step_delay_ms"] / 1000)

        run["status"] = "completed"
        run["completed_at"] = datetime.utcnow()
        run["last_result"] = last_result
        _touch_run(run)
        return last_result
    except asyncio.CancelledError:
        run["status"] = "cancelled"
        run["completed_at"] = datetime.utcnow()
        _touch_run(run)
        raise
    except Exception as exc:
        run["status"] = "failed"
        run["last_error"] = str(exc)
        run["completed_at"] = datetime.utcnow()
        _touch_run(run)
        return run["last_result"]


async def _run_scenario_in_background(shipment_id: str):
    try:
        await _execute_scenario_run(shipment_id)
    except asyncio.CancelledError:
        pass
    finally:
        _scenario_tasks.pop(shipment_id, None)


async def _start_scenario(
    scenario_name: str,
    shipment_id: str,
    *,
    mode: Literal["playback", "full"],
    step_delay_ms: int,
):
    from src.simulator.scenarios import SCENARIOS

    if scenario_name not in SCENARIOS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown scenario '{scenario_name}'. Available: {list(SCENARIOS)}",
        )

    readings = SCENARIOS[scenario_name](shipment_id=shipment_id)
    await init_shipment(shipment_id)

    now = datetime.utcnow()
    run = {
        "scenario_name": scenario_name,
        "mode": mode,
        "status": "running",
        "readings": readings,
        "next_index": 0,
        "processed_readings": 0,
        "total_readings": len(readings),
        "step_delay_ms": step_delay_ms if mode == "playback" else 0,
        "auto_approve_actions": mode == "full",
        "started_at": now,
        "updated_at": now,
        "completed_at": None,
        "last_error": None,
        "last_result": {
            "severity": "LOW",
            "awaiting_approval": False,
            "anomalies": 0,
        },
    }
    _scenario_runs[shipment_id] = run

    if mode == "full":
        final_status = await _execute_scenario_run(shipment_id)
        return {
            "status": run["status"],
            "scenario": scenario_name,
            "scenario_run": _serialize_scenario_run(run),
            "readings_processed": run["processed_readings"],
            "final_status": final_status,
        }

    task = asyncio.create_task(_run_scenario_in_background(shipment_id))
    _scenario_tasks[shipment_id] = task
    return {
        "status": "started",
        "scenario": scenario_name,
        "scenario_run": _serialize_scenario_run(run),
    }


@app.post("/api/shipments/{shipment_id}/init")
async def init_shipment(shipment_id: str):
    await _cancel_scenario_task(shipment_id, drop_run=True)
    _thread_map[shipment_id] = f"{shipment_id}-{uuid.uuid4().hex[:8]}"
    config = _config(shipment_id)
    graph.update_state(config, {**DEFAULT_STATE, "shipment_id": shipment_id})
    return {"status": "initialized", "shipment_id": shipment_id}


@app.post("/api/shipments/{shipment_id}/ingest")
async def ingest_telemetry(shipment_id: str, reading: TelemetryReading):
    return await _invoke_graph_update(
        shipment_id,
        {"latest_reading": reading, "telemetry_window": [reading]},
    )


@app.get("/api/shipments/{shipment_id}/status")
def get_status(shipment_id: str):
    config = _config(shipment_id)
    snapshot = graph.get_state(config)
    if not snapshot or not snapshot.values:
        raise HTTPException(status_code=404, detail="Shipment not found")

    values = snapshot.values
    is_interrupted = bool(snapshot.next)

    tw_raw = values.get("telemetry_window", [])
    tw_dicts = _list_to_dicts(tw_raw)

    lr_raw = values.get("latest_reading")
    latest = _obj_to_dict(lr_raw) or (tw_dicts[-1] if tw_dicts else None)

    anomalies = _list_to_dicts(values.get("anomalies", []))
    audit = _list_to_dicts(values.get("audit_log", []))

    return {
        "shipment_id": shipment_id,
        "severity": values.get("severity", "LOW"),
        "spoilage_probability": values.get("spoilage_probability", 0.0),
        "delay_risk": values.get("delay_risk", 0.0),
        "awaiting_human_approval": values.get("awaiting_human_approval", False) or is_interrupted,
        "orchestrator_reasoning": values.get("orchestrator_reasoning", ""),
        "orchestrator_thinking": values.get("orchestrator_thinking"),
        "recommended_actions": values.get("recommended_actions", []),
        "predicted_breach_minutes": values.get("predicted_breach_minutes"),
        "temperature_forecast": values.get("temperature_forecast", []),
        "anomaly_count": len(anomalies),
        "anomalies": anomalies,
        "notifications_sent": values.get("notifications_sent", []),
        "cold_storage_booked": values.get("cold_storage_booked", False),
        "cold_storage_facility": values.get("cold_storage_facility"),
        "insurance_claim_id": values.get("insurance_claim_id"),
        "inventory_impact": values.get("inventory_impact"),
        "gdp_compliant": values.get("gdp_compliant", True),
        "audit_log": audit[-50:],
        "telemetry_window": tw_dicts[-20:],
        "latest_reading": latest,
        "route_recommendation": _obj_to_dict(values.get("route_recommendation")),
        "scenario_run": _serialize_scenario_run(_scenario_runs.get(shipment_id)),
    }


@app.get("/api/shipments/{shipment_id}/audit")
def get_audit_log(shipment_id: str, limit: int = Query(default=50, le=200)):
    config = _config(shipment_id)
    snapshot = graph.get_state(config)
    if not snapshot or not snapshot.values:
        raise HTTPException(status_code=404, detail="Shipment not found")

    values = snapshot.values
    audit = _list_to_dicts(values.get("audit_log", []))
    return {
        "shipment_id": shipment_id,
        "total_entries": len(audit),
        "gdp_compliant": values.get("gdp_compliant", True),
        "audit_log": audit[-limit:],
    }


@app.post("/api/shipments/{shipment_id}/approve")
async def approve_action(shipment_id: str, decision: HumanDecision):
    config = _config(shipment_id)
    snapshot = graph.get_state(config)
    if not snapshot or not snapshot.values:
        raise HTTPException(status_code=404, detail="Shipment not found")

    next_nodes = set(snapshot.next or ())
    has_pending_approval = bool(snapshot.values.get("awaiting_human_approval", False)) or bool(
        next_nodes & _APPROVAL_RESUME_NODES
    )
    if not has_pending_approval:
        run = _scenario_runs.get(shipment_id)
        detail = "No pending human approval for this shipment"
        if run and run.get("last_error"):
            detail = f"{detail}. Latest scenario error: {run['last_error']}"
        raise HTTPException(status_code=409, detail=detail)

    graph.update_state(config, {
        "human_decision": decision.decision,
        "human_notes": decision.notes,
        "awaiting_human_approval": False,
    })
    result = await asyncio.get_running_loop().run_in_executor(
        None, lambda: graph.invoke(None, config=config)
    ) or {}

    run = _scenario_runs.get(shipment_id)
    if run and run.get("status") == "paused_for_approval" and run.get("next_index", 0) < run.get("total_readings", 0):
        run["status"] = "running"
        run["last_error"] = None
        if decision.decision in {"approved", "modified"}:
            run["auto_approve_actions"] = True
        _touch_run(run)
        task = asyncio.create_task(_run_scenario_in_background(shipment_id))
        _scenario_tasks[shipment_id] = task

    return {
        "status": "resumed",
        "severity": result.get("severity"),
        "actions": result.get("recommended_actions", []),
        "inventory_impact": result.get("inventory_impact"),
    }


@app.post("/api/scenarios/{scenario_name}/run/{shipment_id}")
async def run_scenario(scenario_name: str, shipment_id: str):
    return await _start_scenario(
        scenario_name,
        shipment_id,
        mode="full",
        step_delay_ms=0,
    )


@app.post("/api/scenarios/{scenario_name}/start/{shipment_id}")
async def start_scenario(
    scenario_name: str,
    shipment_id: str,
    mode: Literal["playback", "full"] = "playback",
    step_delay_ms: int = Query(default=800, ge=0, le=10000),
):
    return await _start_scenario(
        scenario_name,
        shipment_id,
        mode=mode,
        step_delay_ms=step_delay_ms,
    )


@app.get("/api/scenarios")
def list_scenarios():
    return {
        "scenarios": ["temp_spike", "customs_hold", "gradual_drift", "compound_failure"],
        "descriptions": {
            "temp_spike": "Refrigeration failure with a severe mid-route temperature spike",
            "customs_hold": "Shipment held at Frankfurt customs with delay escalation",
            "gradual_drift": "Temperature slowly rises toward a cold-chain breach",
            "compound_failure": "Temperature spike plus customs hold in one incident",
        },
        "modes": {
            "playback": "Step-by-step replay that pauses at the human approval gate",
            "full": "Auto-completes the entire scenario for a quick end-to-end demo",
        },
    }


@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}
