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

    inventory_impact: dict | None

    audit_log: Annotated[list[AuditEntry], operator.add]
    gdp_compliant: bool

    awaiting_human_approval: bool
    human_decision: Literal["approved", "rejected", "modified"] | None
    human_notes: str | None

    # Extended thinking — stores Claude's raw reasoning chain from orchestrator
    orchestrator_thinking: str | None

    # Predictive analytics — linear forecast of temperature trajectory
    predicted_breach_minutes: float | None   # None = no breach predicted
    temperature_forecast: list[float]        # next N predicted readings
