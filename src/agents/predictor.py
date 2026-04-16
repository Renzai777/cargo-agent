"""
Predictive Alert Agent — forecasts temperature trajectory before a breach occurs.

Uses linear regression (numpy polyfit) on the telemetry window to extrapolate
future readings. If the projected line crosses the GDP safe-temp threshold,
it reports how many minutes until breach so upstream agents can act proactively.
"""
import numpy as np
from src.graph.state import CargoState, AuditEntry

# GDP cold-chain thresholds (WHO guidelines)
TEMP_MAX: dict[str, float] = {
    "vaccine": 8.0,
    "biologics": 8.0,
    "default": 25.0,
}

# Seconds between telemetry readings (matches simulator cadence)
READING_INTERVAL_SECONDS = 30
FORECAST_STEPS = 20           # predict this many readings forward
MIN_WINDOW = 5                # need at least this many points to regress


def predictor_agent(state: CargoState) -> dict:
    window = state.get("telemetry_window", [])

    if len(window) < MIN_WINDOW:
        return {
            "predicted_breach_minutes": None,
            "temperature_forecast": [],
            "audit_log": [_audit("Insufficient window for forecast", state, "INFO")],
        }

    cargo_type = state.get("cargo_type", "default").lower()
    threshold = TEMP_MAX.get(cargo_type, TEMP_MAX["default"])

    temps = np.array([r.temperature_c for r in window])
    x = np.arange(len(temps), dtype=float)

    # Fit a degree-1 polynomial (linear trend)
    coeffs = np.polyfit(x, temps, 1)
    slope, intercept = coeffs

    # Project FORECAST_STEPS readings into the future
    future_x = np.arange(len(temps), len(temps) + FORECAST_STEPS, dtype=float)
    forecast = list(np.polyval(coeffs, future_x))

    # Determine when (if ever) the forecast crosses the threshold
    predicted_breach_minutes: float | None = None
    if slope > 0:  # temperature rising — only check for breach on upward trend
        for step, temp in enumerate(forecast):
            if temp >= threshold:
                minutes = (step + 1) * READING_INTERVAL_SECONDS / 60
                predicted_breach_minutes = round(minutes, 1)
                break

    if predicted_breach_minutes is not None:
        detail = (
            f"⚠️ Temperature rising at {slope:+.3f}°C/reading. "
            f"Projected breach of {threshold}°C threshold in "
            f"{predicted_breach_minutes:.0f} minutes."
        )
        severity = "HIGH" if predicted_breach_minutes < 15 else "MEDIUM"
    else:
        detail = (
            f"Temperature trend: {slope:+.3f}°C/reading — "
            f"no breach of {threshold}°C threshold predicted in next "
            f"{FORECAST_STEPS * READING_INTERVAL_SECONDS // 60} minutes."
        )
        severity = "LOW"

    return {
        "predicted_breach_minutes": predicted_breach_minutes,
        "temperature_forecast": [round(f, 2) for f in forecast],
        "audit_log": [_audit(detail, state, severity)],
    }


def _audit(detail: str, state: CargoState, severity: str) -> AuditEntry:
    return AuditEntry(
        agent_name="predictor_agent",
        action_type="TEMPERATURE_FORECAST",
        action_detail=detail,
        reasoning="Linear regression (polyfit degree-1) on telemetry window",
        severity=severity,
        gdp_compliant=True,
        shipment_id=state["shipment_id"],
    )
