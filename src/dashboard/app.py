import math
import time
from datetime import datetime

import httpx
import plotly.graph_objects as go
import streamlit as st

API_BASE = "http://localhost:8000"
REFRESH_INTERVAL = 5
SCENARIO_LABELS = {
    "temp_spike": "Temp Spike - refrigeration failure",
    "customs_hold": "Customs Hold - Frankfurt delay",
    "gradual_drift": "Gradual Drift - slow temperature rise",
    "compound_failure": "Compound Failure - spike plus hold",
}

st.set_page_config(page_title="AI Cargo Monitor", layout="wide", initial_sidebar_state="expanded")
st.markdown(
    """
<style>
[data-testid="stAppViewContainer"] { background-color: #0a0a14; }
[data-testid="stSidebar"] { background-color: #0f0f1e; }
.agent-card { background:#1a1a2e; border-radius:8px; padding:10px 14px; margin:4px 0; border-left:3px solid #3b82f6; font-size:0.85rem; }
.agent-card.active { border-left-color:#f59e0b; background:#1e1a0e; }
.agent-card.done { border-left-color:#22c55e; background:#0e1e14; }
.agent-card.waiting { border-left-color:#6b7280; }
.agent-card.critical { border-left-color:#ef4444; background:#1e0e0e; }
.temp-display { font-size:3.8rem; font-weight:900; text-align:center; padding:12px 8px; border-radius:12px; margin:4px 0; letter-spacing:-1px; }
.temp-ok { color:#22c55e; } .temp-warning { color:#f59e0b; } .temp-critical { color:#ef4444; }
</style>
""",
    unsafe_allow_html=True,
)


def fetch_status(shipment_id: str) -> dict | None:
    try:
        response = httpx.get(f"{API_BASE}/api/shipments/{shipment_id}/status", timeout=5)
        return response.json() if response.status_code == 200 else None
    except Exception:
        return None


def run_scenario(scenario: str, shipment_id: str, mode: str) -> dict | None:
    try:
        if mode == "full":
            response = httpx.post(f"{API_BASE}/api/scenarios/{scenario}/run/{shipment_id}", timeout=90)
        else:
            response = httpx.post(
                f"{API_BASE}/api/scenarios/{scenario}/start/{shipment_id}",
                params={"mode": "playback", "step_delay_ms": 800},
                timeout=15,
            )
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        st.error(f"Scenario failed: {exc}")
        return None


def init_shipment(shipment_id: str):
    try:
        httpx.post(f"{API_BASE}/api/shipments/{shipment_id}/init", timeout=15).raise_for_status()
    except Exception as exc:
        st.error(f"Initialization failed: {exc}")


def approve(shipment_id: str, decision: str, notes: str = ""):
    try:
        httpx.post(
            f"{API_BASE}/api/shipments/{shipment_id}/approve",
            json={"decision": decision, "notes": notes},
            timeout=30,
        ).raise_for_status()
    except Exception as exc:
        st.error(f"Approval failed: {exc}")


def temp_class(temp: float) -> str:
    if 2.0 <= temp <= 8.0:
        return "temp-ok"
    if temp <= 10.0:
        return "temp-warning"
    return "temp-critical"


def render_pipeline(status: dict) -> str:
    audit_agents = {entry.get("agent_name") for entry in status.get("audit_log", [])}
    anomalies = status.get("anomalies", [])
    awaiting = status.get("awaiting_human_approval", False)
    recommended = status.get("recommended_actions", [])
    severity = status.get("severity", "LOW")
    steps = [
        ("Monitor Agent", "done" if status.get("latest_reading") else "waiting", False),
        ("Predictor Agent", "done" if status.get("temperature_forecast") or "predictor_agent" in audit_agents else "waiting", False),
        ("Anomaly Detector", "critical" if anomalies else "done" if ("anomaly_agent" in audit_agents or "monitor_agent" in audit_agents) else "waiting", False),
        ("Risk Assessor", "critical" if severity in ("HIGH", "CRITICAL") else "done" if "risk_agent" in audit_agents else "waiting", False),
        ("Decision Orchestrator (HITL)", "critical" if awaiting else "done" if (status.get("orchestrator_reasoning") or recommended) else "waiting", False),
        ("Route Optimizer", "done" if status.get("route_recommendation") else "active" if awaiting and "REROUTE" in recommended else "waiting", True),
        ("Notification Agent", "done" if status.get("notifications_sent") else "active" if awaiting and "NOTIFY_HOSPITALS" in recommended else "waiting", True),
        ("Inventory Forecast", "done" if status.get("inventory_impact") else "active" if awaiting and "NOTIFY_HOSPITALS" in recommended else "waiting", True),
        ("Cold Storage", "done" if status.get("cold_storage_booked") else "active" if awaiting and "COLD_STORAGE" in recommended else "waiting", True),
        ("Insurance Claim", "done" if status.get("insurance_claim_id") else "active" if awaiting and "FILE_INSURANCE" in recommended else "waiting", True),
        ("Compliance Logger", "done" if status.get("audit_log") else "waiting", True),
    ]
    icons = {"done": "[x]", "active": "[>]", "waiting": "[ ]", "critical": "[!]"}
    return "".join(
        f'<div class="agent-card {state}">{"&nbsp;&nbsp;&nbsp;- " if child else ""}{icons[state]} {label}</div>'
        for label, state, child in steps
    )


def triggered_actions(status: dict) -> int:
    return sum([
        1 if status.get("route_recommendation") else 0,
        1 if status.get("notifications_sent") else 0,
        1 if status.get("inventory_impact") else 0,
        1 if status.get("cold_storage_booked") else 0,
        1 if status.get("insurance_claim_id") else 0,
    ])


with st.sidebar:
    st.markdown("## AI Cargo Monitor")
    st.caption("UMD Agentic AI Hackathon 2026 · Case 6")
    st.divider()
    shipment_id = st.text_input("Shipment ID", value="SHP-DEMO-001")
    selected = st.selectbox("Scenario", list(SCENARIO_LABELS), format_func=lambda key: SCENARIO_LABELS[key])
    st.caption("Run Live shows the agent flow step-by-step. Run Full auto-completes the whole scenario.")
    live_col, full_col = st.columns(2)
    if live_col.button("Run Live", type="primary", use_container_width=True):
        if run_scenario(selected, shipment_id, "playback"):
            st.rerun()
    if full_col.button("Run Full", use_container_width=True):
        if run_scenario(selected, shipment_id, "full"):
            st.rerun()
    if st.button("Initialize Shipment", use_container_width=True):
        init_shipment(shipment_id)
        st.rerun()
    auto_refresh = st.toggle("Auto-refresh dashboard", value=True)


status = fetch_status(shipment_id)
if not status:
    st.markdown("## AI Cargo Monitor")
    st.warning("No shipment data found. Initialize a shipment or run a scenario from the sidebar.")
    st.stop()

severity = status.get("severity", "LOW")
telemetry = status.get("telemetry_window", [])
latest = status.get("latest_reading")
audit = status.get("audit_log", [])
scenario_run = status.get("scenario_run") or {}
refresh_interval = 1 if scenario_run.get("status") == "running" else REFRESH_INTERVAL

with st.sidebar:
    st.divider()
    if scenario_run:
        st.markdown("**Scenario Replay**")
        st.caption(SCENARIO_LABELS.get(scenario_run.get("scenario_name", ""), scenario_run.get("scenario_name", "")))
        st.caption(f"{'Live Playback' if scenario_run.get('mode') == 'playback' else 'Full Replay'} · {str(scenario_run.get('status', 'idle')).replace('_', ' ').title()}")
        st.progress(min(max(float(scenario_run.get("progress_pct", 0.0)) / 100, 0.0), 1.0))
        st.caption(f"Step {scenario_run.get('processed_readings', 0)}/{scenario_run.get('total_readings', 0)}")
        if scenario_run.get("last_error"):
            st.error(scenario_run["last_error"])
    st.divider()
    st.markdown("**Agent Pipeline**")
    st.markdown(render_pipeline(status), unsafe_allow_html=True)
    if auto_refresh:
        st.caption(f"Auto-refresh every {refresh_interval}s")


st.markdown(f"## {severity} AI Cargo Monitor - `{shipment_id}`")
st.caption(f"Last refresh: {datetime.now().strftime('%H:%M:%S')}")
if scenario_run:
    replay_text = f"{'Live Playback' if scenario_run.get('mode') == 'playback' else 'Full Replay'} · {str(scenario_run.get('status', 'idle')).replace('_', ' ').title()} · step {scenario_run.get('processed_readings', 0)}/{scenario_run.get('total_readings', 0)}"
    (st.warning if scenario_run.get("status") == "paused_for_approval" else st.success if scenario_run.get("status") == "completed" else st.info)(replay_text)

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Severity", severity)
k2.metric("Spoilage Risk", f"{status.get('spoilage_probability', 0.0):.0%}")
k3.metric("Delay Risk", f"{status.get('delay_risk', 0.0):.0%}")
k4.metric("Anomalies", status.get("anomaly_count", 0))
k5.metric("Audit Entries", len(audit))
k6.metric("GDP Compliant", "Yes" if status.get("gdp_compliant", True) else "No")

st.info(
    "Agentic flow: "
    f"predictive monitoring {'active' if (status.get('predicted_breach_minutes') is not None or status.get('temperature_forecast')) else 'standby'} | "
    f"HITL {'waiting' if status.get('awaiting_human_approval') else 'ready'} | "
    f"cascading actions {triggered_actions(status)}/5 | audit trail {len(audit)} events"
)

if status.get("predicted_breach_minutes") is not None:
    mins = status["predicted_breach_minutes"]
    (st.error if mins <= 10 else st.warning if mins <= 30 else st.info)(
        f"Predicted breach in {mins:.1f} min if the current trend continues."
    )

if status.get("awaiting_human_approval"):
    st.error("## HUMAN APPROVAL REQUIRED")
    with st.container(border=True):
        left, right = st.columns([3, 2])
        left.markdown("**Orchestrator Reasoning**")
        left.info(status.get("orchestrator_reasoning", "No reasoning available") or "Awaiting model response...")
        right.markdown("**Recommended Actions**")
        for action in status.get("recommended_actions", []):
            right.markdown(f"- **{action}**")
        notes = st.text_input("Modification notes", key="modify_notes")
        a_col, r_col, m_col = st.columns(3)
        if a_col.button("Approve", type="primary", use_container_width=True):
            approve(shipment_id, "approved")
            time.sleep(1)
            st.rerun()
        if r_col.button("Reject", use_container_width=True):
            approve(shipment_id, "rejected", notes="Manual override")
            st.rerun()
        if m_col.button("Approve with notes", use_container_width=True):
            approve(shipment_id, "modified", notes=notes or "Modified approval")
            st.rerun()


row1_left, row1_right = st.columns([3, 2])
route_lats, route_lons = [40.7128, 50.1109, -1.2921], [-74.0060, 8.6821, 36.8219]
leg1 = math.dist((route_lats[0], route_lons[0]), (route_lats[1], route_lons[1]))
leg2 = math.dist((route_lats[1], route_lons[1]), (route_lats[2], route_lons[2]))
total_route = leg1 + leg2

with row1_left:
    fig = go.Figure()
    fig.add_trace(go.Scattergeo(lat=route_lats, lon=route_lons, mode="lines", line=dict(width=2, color="rgba(100,120,180,0.35)", dash="dot"), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scattergeo(lat=route_lats, lon=route_lons, mode="markers+text", marker=dict(size=12, color=["#3b82f6", "#ef4444" if severity in ("HIGH", "CRITICAL") else "#22c55e", "#3b82f6"], line=dict(width=2, color="white")), text=["New York", "Frankfurt", "Nairobi"], textposition=["middle right", "top center", "middle right"], textfont=dict(color="white", size=10), name="Waypoints"))
    progress_pct, travelled_km, remaining_km, segment = 0.0, 0.0, total_route, "Awaiting departure"
    if telemetry:
        lats = [item["latitude"] for item in telemetry]
        lons = [item["longitude"] for item in telemetry]
        temps = [item["temperature_c"] for item in telemetry]
        current = telemetry[-1]
        progress_pct = min(max(len(telemetry) / max(scenario_run.get("total_readings", len(telemetry) or 1), 1) * 100, 0.0), 100.0) if scenario_run else 0.0
        for idx in range(len(lats) - 1):
            fig.add_trace(go.Scattergeo(lat=[lats[idx], lats[idx + 1]], lon=[lons[idx], lons[idx + 1]], mode="lines", line=dict(width=4, color="#ef4444" if temps[idx] > 8.0 else "#22c55e"), showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scattergeo(lat=[current["latitude"]], lon=[current["longitude"]], mode="markers+text", marker=dict(size=22, color="#ef4444" if severity in ("HIGH", "CRITICAL") else "#22c55e", line=dict(width=3, color="white")), text=[f"  {current['temperature_c']:.1f}C"], textposition="middle right", textfont=dict(color="white", size=14, family="monospace"), name="Current Position"))
        travelled_km = progress_pct / 100 * total_route
        remaining_km = max(total_route - travelled_km, 0.0)
        segment = "In transit"
    fig.update_layout(geo=dict(projection_type="natural earth", showland=True, landcolor="#1a2035", showocean=True, oceancolor="#0d1520", showcountries=True, countrycolor="rgba(80,100,160,0.45)", showcoastlines=True, coastlinecolor="rgba(80,100,160,0.55)", showframe=False, bgcolor="#0f0f1a"), paper_bgcolor="#0f0f1a", font_color="white", margin=dict(l=0, r=0, t=0, b=0), height=340)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    replay_note = f" · replay step {scenario_run.get('processed_readings', 0)}/{scenario_run.get('total_readings', 0)}" if scenario_run else ""
    st.markdown(f"**Journey Progress** `{progress_pct:.1f}%` <span style='color:#9ca3af;font-size:0.85rem'>{travelled_km:,.0f} units travelled · {remaining_km:,.0f} units remaining · {len(telemetry)} sensor readings{replay_note}</span>", unsafe_allow_html=True)
    st.progress(progress_pct / 100)

with row1_right:
    st.markdown("### Current Reading")
    if latest:
        st.markdown(f'<div class="temp-display {temp_class(latest["temperature_c"])}">{latest["temperature_c"]}C</div>', unsafe_allow_html=True)
        st.caption("Safe range: 2-8C for vaccines")
        c1, c2 = st.columns(2)
        c1.metric("Humidity", f"{latest['humidity_pct']}%")
        c2.metric("Shock", f"{latest['shock_g']}g")
        c1.metric("Altitude", f"{int(latest['altitude_m']):,}m")
        c2.metric("Customs", latest["customs_status"].replace("_", " ").title())
    else:
        st.info("Awaiting first telemetry reading.")

st.divider()
if telemetry:
    st.markdown("### Sensor Timeline")
    xs = list(range(len(telemetry)))
    tc, hc, sc = st.columns(3)
    temps = [item["temperature_c"] for item in telemetry]
    humids = [item["humidity_pct"] for item in telemetry]
    shocks = [item["shock_g"] for item in telemetry]
    temp_fig = go.Figure([go.Scatter(x=xs, y=temps, mode="lines+markers", line=dict(color="#ef4444"))])
    if status.get("temperature_forecast"):
        future_x = list(range(len(xs), len(xs) + len(status["temperature_forecast"])))
        temp_fig.add_trace(go.Scatter(x=[xs[-1]] + future_x, y=[temps[-1]] + status["temperature_forecast"], mode="lines", line=dict(color="#f97316", dash="dot"), name="AI Forecast"))
    temp_fig.add_hline(y=8.0, line_dash="dash", line_color="#f59e0b")
    temp_fig.add_hline(y=2.0, line_dash="dash", line_color="#3b82f6")
    temp_fig.update_layout(title="Temperature", height=220, paper_bgcolor="#0f0f1a", plot_bgcolor="#0a0a14", font_color="white", margin=dict(l=30, r=10, t=40, b=30))
    humid_fig = go.Figure([go.Scatter(x=xs, y=humids, mode="lines+markers", line=dict(color="#3b82f6"))])
    humid_fig.add_hline(y=75.0, line_dash="dash", line_color="#f59e0b")
    humid_fig.update_layout(title="Humidity", height=220, paper_bgcolor="#0f0f1a", plot_bgcolor="#0a0a14", font_color="white", margin=dict(l=30, r=10, t=40, b=30))
    shock_fig = go.Figure([go.Bar(x=xs, y=shocks, marker_color=["#ef4444" if item > 2.0 else "#8b5cf6" for item in shocks])])
    shock_fig.add_hline(y=2.0, line_dash="dash", line_color="#f59e0b")
    shock_fig.update_layout(title="Shock", height=220, paper_bgcolor="#0f0f1a", plot_bgcolor="#0a0a14", font_color="white", margin=dict(l=30, r=10, t=40, b=30))
    tc.plotly_chart(temp_fig, use_container_width=True)
    hc.plotly_chart(humid_fig, use_container_width=True)
    sc.plotly_chart(shock_fig, use_container_width=True)

st.divider()
st.markdown("### Cascading Actions")
a1, a2, a3, a4, a5 = st.columns(5)
route_rec = status.get("route_recommendation")
notifications = status.get("notifications_sent", [])
inventory = status.get("inventory_impact")
a1.metric("Reroute", route_rec["carrier"] if route_rec else "Not triggered")
a2.metric("Hospitals", f"{len(notifications)} notified" if notifications else "Not triggered")
a3.metric("Inventory", f"{inventory['expected_usable_doses']} usable" if inventory else "Not triggered")
a4.metric("Cold Storage", status.get("cold_storage_facility") or ("Booked" if status.get("cold_storage_booked") else "Not triggered"))
a5.metric("Insurance", status.get("insurance_claim_id") or "Not triggered")

if status.get("anomalies"):
    with st.expander(f"Detected Anomalies ({len(status['anomalies'])})", expanded=severity in ("HIGH", "CRITICAL")):
        for anomaly in status["anomalies"]:
            st.markdown(f"**{anomaly['anomaly_type'].replace('_', ' ').title()}** - {anomaly['description']}")
            st.caption(f"Raw: {anomaly['raw_value']} · Threshold: {anomaly['threshold_value']} · Z-score: {anomaly.get('z_score', 'N/A')}")

st.markdown("### Audit Trail")
if audit:
    for entry in reversed(audit[-15:]):
        with st.expander(f"[{entry['agent_name']}] {entry['action_type']} · {entry.get('timestamp', '')[:19]}"):
            st.markdown(f"**Action:** {entry['action_detail']}")
            st.markdown(f"**Reasoning:** {entry['reasoning'][:400]}")
            st.caption(f"GDP Compliant: {'Yes' if entry['gdp_compliant'] else 'No'} · Severity: {entry.get('severity', 'INFO')}")
else:
    st.caption("No audit entries yet.")

if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()
