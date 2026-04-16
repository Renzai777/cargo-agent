import asyncio

import pytest
from fastapi import HTTPException

from src.agents import anomaly_detector, orchestrator, risk_assessor
from src.api import main as api_main
from src.graph.state import HumanDecision


def _enable_demo_mode(monkeypatch):
    monkeypatch.setattr(anomaly_detector, "DEMO_MODE", True)
    monkeypatch.setattr(risk_assessor, "DEMO_MODE", True)
    monkeypatch.setattr(orchestrator, "DEMO_MODE", True)


async def _wait_for_run_state(shipment_id: str, *, timeout_s: float = 1.0) -> dict:
    deadline = asyncio.get_event_loop().time() + timeout_s
    while asyncio.get_event_loop().time() < deadline:
        status = api_main.get_status(shipment_id)
        run = status.get("scenario_run") or {}
        if run.get("processed_readings", 0) > 0 and run.get("status") != "running":
            return status
        await asyncio.sleep(0.02)
    return api_main.get_status(shipment_id)


@pytest.mark.asyncio
async def test_live_playback_does_not_jump_to_complete(monkeypatch):
    _enable_demo_mode(monkeypatch)
    shipment_id = "SHP-API-LIVE"

    await api_main.start_scenario("temp_spike", shipment_id, mode="playback", step_delay_ms=0)
    status = await _wait_for_run_state(shipment_id)
    run = status["scenario_run"]

    assert run["status"] in {"running", "paused_for_approval"}
    assert run["processed_readings"] < run["total_readings"]

    await api_main.init_shipment(shipment_id)


@pytest.mark.asyncio
async def test_full_scenario_completes(monkeypatch):
    _enable_demo_mode(monkeypatch)
    shipment_id = "SHP-API-FULL"

    result = await api_main.start_scenario("temp_spike", shipment_id, mode="full", step_delay_ms=0)
    run = result["scenario_run"]

    assert result["status"] == "completed"
    assert run["status"] == "completed"
    assert run["processed_readings"] == run["total_readings"]

    await api_main.init_shipment(shipment_id)


@pytest.mark.asyncio
async def test_approval_resumes_paused_playback(monkeypatch):
    _enable_demo_mode(monkeypatch)
    shipment_id = "SHP-API-RESUME"

    await api_main.start_scenario("temp_spike", shipment_id, mode="playback", step_delay_ms=0)
    status = await _wait_for_run_state(shipment_id)
    before = status["scenario_run"]["processed_readings"]

    await api_main.approve_action(shipment_id, HumanDecision(decision="approved", notes=""))
    await asyncio.sleep(0.05)
    after = api_main.get_status(shipment_id)["scenario_run"]["processed_readings"]

    assert after > before

    await api_main.init_shipment(shipment_id)


@pytest.mark.asyncio
async def test_approved_playback_finishes_remaining_steps(monkeypatch):
    _enable_demo_mode(monkeypatch)
    shipment_id = "SHP-API-FINISH"

    await api_main.start_scenario("temp_spike", shipment_id, mode="playback", step_delay_ms=0)
    status = await _wait_for_run_state(shipment_id)
    assert status["scenario_run"]["status"] == "paused_for_approval"

    await api_main.approve_action(shipment_id, HumanDecision(decision="approved", notes=""))
    for _ in range(100):
        run = api_main.get_status(shipment_id)["scenario_run"]
        if run["status"] == "completed":
            break
        await asyncio.sleep(0.02)

    assert api_main.get_status(shipment_id)["scenario_run"]["status"] == "completed"

    await api_main.init_shipment(shipment_id)


@pytest.mark.asyncio
async def test_approve_without_pending_request_returns_409():
    shipment_id = "SHP-API-NO-PENDING"

    await api_main.init_shipment(shipment_id)
    with pytest.raises(HTTPException) as exc_info:
        await api_main.approve_action(shipment_id, HumanDecision(decision="approved", notes=""))

    assert exc_info.value.status_code == 409
    assert "No pending human approval" in exc_info.value.detail
