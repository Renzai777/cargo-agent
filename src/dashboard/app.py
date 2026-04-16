"""
AI Cargo Monitor — Streamlit Dashboard
UMD Agentic AI Hackathon 2026 · Case 6
"""
import time
import httpx
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime

API_BASE = "http://localhost:8000"
REFRESH_INTERVAL = 5

st.set_page_config(
    page_title="AI Cargo Monitor",
    page_icon="🌡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
/* Dark theme base */
[data-testid="stAppViewContainer"] { background-color: #0a0a14; }
[data-testid="stSidebar"] { background-color: #0f0f1e; }

/* Agent pipeline cards */
.agent-card {
    background: #1a1a2e; border-radius: 8px; padding: 10px 14px;
    margin: 4px 0; border-left: 3px solid #3b82f6; font-size: 0.85rem;
}
.agent-card.active  { border-left-color: #f59e0b; background: #1e1a0e; animation: pulse 1s infinite; }
.agent-card.done    { border-left-color: #22c55e; background: #0e1e14; }
.agent-card.waiting { border-left-color: #6b7280; }
.agent-card.critical { border-left-color: #ef4444; background: #1e0e0e; }

/* Severity badge */
.sev-critical { color: #ef4444; font-weight: 700; font-size: 1.3rem; }
.sev-high     { color: #f97316; font-weight: 700; font-size: 1.3rem; }
.sev-medium   { color: #eab308; font-weight: 700; font-size: 1.3rem; }
.sev-low      { color: #22c55e; font-weight: 700; font-size: 1.3rem; }

/* Current temp big display */
.temp-display {
    font-size: 3.8rem; font-weight: 900; text-align: center;
    padding: 12px 8px; border-radius: 12px; margin: 4px 0;
    letter-spacing: -1px;
}

/* Reading card wrapper */
.reading-card {
    background: #111827; border-radius: 12px; padding: 14px;
    border: 1px solid #1e293b; margin-bottom: 10px;
}
.temp-ok       { color: #22c55e; }
.temp-warning  { color: #f59e0b; }
.temp-critical { color: #ef4444; }

@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.6; } }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────── helpers ──────────────────────────────────────
def fetch_status(shipment_id: str) -> dict | None:
    try:
        r = httpx.get(f"{API_BASE}/api/shipments/{shipment_id}/status", timeout=5)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


def run_scenario(scenario: str, shipment_id: str):
    try:
        httpx.post(f"{API_BASE}/api/scenarios/{scenario}/run/{shipment_id}", timeout=90)
    except Exception as e:
        st.error(f"Scenario failed: {e}")


def approve(shipment_id: str, decision: str, notes: str = ""):
    try:
        httpx.post(
            f"{API_BASE}/api/shipments/{shipment_id}/approve",
            json={"decision": decision, "notes": notes},
            timeout=30,
        )
    except Exception as e:
        st.error(f"Approval failed: {e}")


def temp_color_class(temp: float, cargo_type: str = "vaccine") -> str:
    if cargo_type == "vaccine":
        if 2.0 <= temp <= 8.0:
            return "temp-ok"
        if temp <= 10.0:
            return "temp-warning"
    return "temp-critical"


def severity_icon(sev: str) -> str:
    return {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🟠", "CRITICAL": "🔴"}.get(sev, "⚪")


# ─────────────────────────────── sidebar ──────────────────────────────────────
with st.sidebar:
    st.markdown("## 🌡️ AI Cargo Monitor")
    st.caption("UMD Agentic AI Hackathon 2026 · Case 6")
    st.divider()

    st.markdown("### Shipment")
    shipment_id = st.text_input("Shipment ID", value="SHP-DEMO-001", label_visibility="collapsed")

    st.markdown("### Inject Scenario")
    scenario_labels = {
        "temp_spike":       "🔥 Temp Spike — refrigeration failure",
        "customs_hold":     "🛂 Customs Hold — Frankfurt delay",
        "gradual_drift":    "📈 Gradual Drift — slow temp rise",
        "compound_failure": "💥 Compound Failure — spike + hold",
    }
    selected = st.selectbox(
        "Scenario", list(scenario_labels.keys()),
        format_func=lambda k: scenario_labels[k]
    )
    if st.button("▶ Run Scenario", type="primary", use_container_width=True):
        with st.spinner(f"Running {selected}..."):
            run_scenario(selected, shipment_id)
        st.success("Done — refreshing...")
        st.rerun()

    st.divider()
    if st.button("🔄 Initialize Shipment", use_container_width=True):
        httpx.post(f"{API_BASE}/api/shipments/{shipment_id}/init")
        st.success("Initialized")
        st.rerun()

    st.divider()
    auto_refresh = st.toggle("Auto-refresh every 5s", value=True)

    st.divider()
    st.markdown("**Agent Pipeline**")
    st.markdown("""
<div class="agent-card done">✅ Monitor Agent</div>
<div class="agent-card done">✅ Anomaly Detector</div>
<div class="agent-card done">✅ Risk Assessor</div>
<div class="agent-card waiting">⏸ Decision Orchestrator (HITL)</div>
<div style="padding-left:12px">
<div class="agent-card waiting">↳ Route Optimizer</div>
<div class="agent-card waiting">↳ Notification Agent</div>
<div class="agent-card waiting">↳ Inventory Forecast</div>
<div class="agent-card waiting">↳ Cold Storage</div>
<div class="agent-card waiting">↳ Insurance Claim</div>
<div class="agent-card waiting">↳ Compliance Logger</div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────── fetch data ───────────────────────────────────
status = fetch_status(shipment_id)

if not status:
    st.markdown("## 🌡️ AI Cargo Monitor")
    st.warning("No shipment data found. Initialize a shipment or run a scenario from the sidebar.")
    col1, col2 = st.columns(2)
    if col1.button("Initialize SHP-DEMO-001", type="primary"):
        httpx.post(f"{API_BASE}/api/shipments/{shipment_id}/init")
        st.rerun()
    st.stop()

severity    = status.get("severity", "LOW")
spoilage    = status.get("spoilage_probability", 0.0)
delay_risk  = status.get("delay_risk", 0.0)
telemetry   = status.get("telemetry_window", [])
latest      = status.get("latest_reading")
audit       = status.get("audit_log", [])
anomalies   = status.get("anomalies", [])
inv_impact  = status.get("inventory_impact")

# ─────────────────────────────── top header ───────────────────────────────────
hcol1, hcol2 = st.columns([6, 1])
with hcol1:
    st.markdown(f"## {severity_icon(severity)} AI Cargo Monitor — `{shipment_id}`")
with hcol2:
    st.caption(f"Last refresh: {datetime.now().strftime('%H:%M:%S')}")

# ─────────────────────────────── KPI strip ────────────────────────────────────
k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Severity",       f"{severity_icon(severity)} {severity}")
k2.metric("Spoilage Risk",  f"{spoilage:.0%}", delta=f"{spoilage:.0%}" if spoilage > 0.3 else None, delta_color="inverse")
k3.metric("Delay Risk",     f"{delay_risk:.0%}")
k4.metric("Anomalies",      status.get("anomaly_count", 0))
k5.metric("Audit Entries",  len(audit))
k6.metric("GDP Compliant",  "✅ Yes" if status.get("gdp_compliant", True) else "❌ No")

st.divider()

# ─────────────────────────────── HITL modal ───────────────────────────────────
if status.get("awaiting_human_approval"):
    st.error("## ⚠️ HUMAN APPROVAL REQUIRED — Pipeline Paused")
    with st.container(border=True):
        c_reason, c_actions = st.columns([3, 2])
        with c_reason:
            st.markdown("**🤖 Orchestrator Reasoning:**")
            st.info(status.get("orchestrator_reasoning", "No reasoning available") or "Awaiting Claude response...")
        with c_actions:
            st.markdown("**🎯 Recommended Actions:**")
            for act in status.get("recommended_actions", []):
                icon = {"REROUTE": "✈️", "NOTIFY_HOSPITALS": "🏥", "COLD_STORAGE": "❄️",
                        "FILE_INSURANCE": "📄", "CUSTOMS_ESCALATE": "🛂"}.get(act, "▶")
                st.markdown(f"- {icon} **{act}**")

        st.markdown("---")
        col_a, col_r, col_m = st.columns(3)
        if col_a.button("✅ **APPROVE** — Execute all actions", type="primary", use_container_width=True):
            approve(shipment_id, "approved")
            st.success("Approved! Agents resuming...")
            time.sleep(1)
            st.rerun()
        if col_r.button("❌ **REJECT** — No action", use_container_width=True):
            approve(shipment_id, "rejected", notes="Manual override — operator decision")
            st.rerun()
        if col_m.button("✏️ **MODIFY** — Approve with notes", use_container_width=True):
            notes = st.text_input("Modification notes")
            if notes:
                approve(shipment_id, "modified", notes=notes)
                st.rerun()
    st.divider()

# ─────────────────────────────── main layout ──────────────────────────────────
row1_left, row1_right = st.columns([3, 2])

# ── Live map ──
with row1_left:
    import math

    # Route waypoints
    ROUTE_LATS = [40.7128, 50.1109, -1.2921]
    ROUTE_LONS = [-74.0060,  8.6821, 36.8219]
    CITIES     = ["New York", "Frankfurt", "Nairobi"]
    CITY_ROLES = ["Origin", "Transit Hub", "Destination"]

    sev_banner_color = {"LOW": "#22c55e", "MEDIUM": "#eab308",
                        "HIGH": "#f97316", "CRITICAL": "#ef4444"}.get(severity, "#9ca3af")
    pos_color = {"HIGH": "#ef4444", "CRITICAL": "#ef4444",
                 "MEDIUM": "#f59e0b"}.get(severity, "#22c55e")

    # ── Compute journey progress for zoom + progress bar ──
    def _haversine(la1, lo1, la2, lo2):
        R = 6371
        dl = math.radians(lo2 - lo1); dp = math.radians(la2 - la1)
        a = math.sin(dp/2)**2 + math.cos(math.radians(la1)) * math.cos(math.radians(la2)) * math.sin(dl/2)**2
        return 2 * R * math.asin(math.sqrt(a))

    total_dist = _haversine(ROUTE_LATS[0], ROUTE_LONS[0], ROUTE_LATS[2], ROUTE_LONS[2])

    fig_map = go.Figure()

    # ── Full planned route backbone (dim dashed) ──
    fig_map.add_trace(go.Scattergeo(
        lat=ROUTE_LATS, lon=ROUTE_LONS, mode="lines",
        line=dict(width=2, color="rgba(100,120,180,0.35)", dash="dot"),
        hoverinfo="skip", showlegend=False,
    ))

    # ── City pins ──
    city_colors = [pos_color if i == 1 else "#3b82f6" for i in range(3)]
    fig_map.add_trace(go.Scattergeo(
        lat=ROUTE_LATS, lon=ROUTE_LONS,
        mode="markers+text",
        marker=dict(size=12, color=city_colors,
                    symbol="circle", line=dict(width=2, color="white")),
        text=[f"<b>{c}</b><br><i>{r}</i>" for c, r in zip(CITIES, CITY_ROLES)],
        textposition=["middle right", "top center", "middle right"],
        textfont=dict(color="white", size=10),
        name="Waypoints",
        hovertemplate="%{text}<extra></extra>",
    ))

    prog_pct   = 0.0
    cur_lat    = ROUTE_LATS[0]
    cur_lon    = ROUTE_LONS[0]
    n_readings = 0
    cur_segment = "Awaiting departure"

    if telemetry:
        lats  = [r["latitude"]  for r in telemetry]
        lons  = [r["longitude"] for r in telemetry]
        temps = [r["temperature_c"] for r in telemetry]
        n_readings = len(telemetry)
        lt    = telemetry[-1]
        cur_lat, cur_lon = lt["latitude"], lt["longitude"]

        # Progress % along total route
        dist_travelled = _haversine(ROUTE_LATS[0], ROUTE_LONS[0], cur_lat, cur_lon)
        prog_pct = min(dist_travelled / total_dist * 100, 100.0)

        # Current flight leg label
        d_to_fra = _haversine(cur_lat, cur_lon, ROUTE_LATS[1], ROUTE_LONS[1])
        d_to_nbo = _haversine(cur_lat, cur_lon, ROUTE_LATS[2], ROUTE_LONS[2])
        if d_to_fra < 200:
            cur_segment = "🛬 Approaching Frankfurt"
        elif d_to_nbo < 500:
            cur_segment = "✈️ NYC → Frankfurt"
        else:
            cur_segment = "✈️ Frankfurt → Nairobi"

        # ── Travelled path segments coloured by temp ──
        for i in range(len(lats) - 1):
            seg_col = "#ef4444" if temps[i] > 8.0 else "#22c55e"
            fig_map.add_trace(go.Scattergeo(
                lat=[lats[i], lats[i+1]], lon=[lons[i], lons[i+1]],
                mode="lines", line=dict(width=4, color=seg_col),
                showlegend=False, hoverinfo="skip",
            ))

        # ── Fading historical dots (most recent = opaque, oldest = transparent) ──
        n = len(lats)
        opacities = [0.15 + 0.7 * (i / max(n-1, 1)) for i in range(n)]
        sizes     = [4 + 4 * (i / max(n-1, 1)) for i in range(n)]
        dot_colors = ["#ef4444" if t > 8.0 else "#22c55e" for t in temps]
        fig_map.add_trace(go.Scattergeo(
            lat=lats[:-1], lon=lons[:-1],
            mode="markers",
            marker=dict(
                size=sizes[:-1],
                color=dot_colors[:-1],
                opacity=opacities[:-1],
                line=dict(width=0),
            ),
            text=[f"{t:.1f}°C" for t in temps[:-1]],
            hovertemplate="Reading: %{text}<extra></extra>",
            name="Sensor History",
        ))

        # ── Ripple ring (larger transparent circle behind current dot) ──
        # Convert pos_color hex (#rrggbb) → rgba with 0.6 alpha for the ring
        _r = int(pos_color[1:3], 16)
        _g = int(pos_color[3:5], 16)
        _b = int(pos_color[5:7], 16)
        ring_color = f"rgba({_r},{_g},{_b},0.55)"
        fig_map.add_trace(go.Scattergeo(
            lat=[cur_lat], lon=[cur_lon], mode="markers",
            marker=dict(size=40, color="rgba(0,0,0,0)",
                        line=dict(width=3, color=ring_color)),
            hoverinfo="skip", showlegend=False,
        ))

        # ── Current position dot ──
        fig_map.add_trace(go.Scattergeo(
            lat=[cur_lat], lon=[cur_lon],
            mode="markers+text",
            marker=dict(size=22, color=pos_color,
                        symbol="circle",
                        line=dict(width=3, color="white")),
            text=[f"  {lt['temperature_c']:.1f}°C"],
            textposition="middle right",
            textfont=dict(color="white", size=14, family="monospace"),
            name="▶ Current Position",
            hovertemplate=(
                f"<b>📍 Current Position</b><br>"
                f"Lat: {cur_lat:.3f}°  Lon: {cur_lon:.3f}°<br>"
                f"Temp: <b>{lt['temperature_c']}°C</b><br>"
                f"Humidity: {lt['humidity_pct']}%<br>"
                f"Altitude: {int(lt['altitude_m']):,}m<br>"
                f"Customs: {lt['customs_status']}<extra></extra>"
            ),
        ))

    # ── Dynamic zoom: tighter box around the active segment ──
    pad = 18
    if telemetry:
        lon_min = min(min(lons), ROUTE_LONS[0], ROUTE_LONS[2]) - pad
        lon_max = max(max(lons), ROUTE_LONS[0], ROUTE_LONS[2]) + pad
        lat_min = min(min(lats), ROUTE_LATS[0], ROUTE_LATS[2]) - pad
        lat_max = max(max(lats), ROUTE_LATS[0], ROUTE_LATS[2]) + pad
    else:
        lon_min, lon_max = -85, 50
        lat_min, lat_max = -15, 62

    fig_map.update_layout(
        geo=dict(
            projection_type="natural earth",
            showland=True,        landcolor="#1a2035",
            showocean=True,       oceancolor="#0d1520",
            showlakes=True,       lakecolor="#0d1520",
            showrivers=False,
            showcountries=True,   countrycolor="rgba(80,100,160,0.45)",
            showcoastlines=True,  coastlinecolor="rgba(80,100,160,0.55)",
            showframe=False,
            bgcolor="#0f0f1a",
            lonaxis=dict(range=[lon_min, lon_max]),
            lataxis=dict(range=[lat_min, lat_max]),
        ),
        paper_bgcolor="#0f0f1a",
        font_color="white",
        margin=dict(l=0, r=0, t=0, b=0),
        height=340,
        legend=dict(
            orientation="h", x=0.01, y=0.01,
            bgcolor="rgba(15,15,26,0.85)",
            bordercolor="rgba(80,100,160,0.4)",
            borderwidth=1, font=dict(size=11),
        ),
        annotations=[
            dict(
                text=f"● {severity}",
                x=0.01, y=0.98, xref="paper", yref="paper",
                showarrow=False,
                font=dict(color=sev_banner_color, size=13, family="monospace"),
                bgcolor="rgba(15,15,26,0.85)",
                bordercolor=sev_banner_color, borderwidth=1, borderpad=5,
            ),
            dict(
                text=f"{cur_segment}",
                x=0.99, y=0.98, xref="paper", yref="paper",
                showarrow=False,
                font=dict(color="#a0aec0", size=11, family="monospace"),
                bgcolor="rgba(15,15,26,0.85)",
                bordercolor="rgba(80,100,160,0.4)", borderwidth=1, borderpad=5,
                xanchor="right",
            ),
        ],
    )
    st.plotly_chart(fig_map, use_container_width=True, config={"displayModeBar": False})

    # ── Progress bar + stats row beneath map ──
    p1, p2, p3, p4 = st.columns([3, 1, 1, 1])
    with p1:
        st.markdown(f"**Journey Progress** &nbsp; `{prog_pct:.1f}%`")
        st.progress(prog_pct / 100)
    p2.metric("Readings", n_readings)
    p3.metric("Travelled", f"{prog_pct/100*total_dist:,.0f} km")
    p4.metric("Remaining", f"{(1-prog_pct/100)*total_dist:,.0f} km")

# ── Current reading + gauges ──
with row1_right:
    st.markdown("### 📊 Current Reading")
    if latest:
        temp_c = latest["temperature_c"]
        tc = temp_color_class(temp_c)
        st.markdown(
            f'<div class="temp-display {tc}">{temp_c}°C</div>',
            unsafe_allow_html=True
        )
        st.caption("Safe range: 2–8°C for vaccines")

        g1, g2 = st.columns(2)
        g1.metric("Humidity",  f"{latest['humidity_pct']}%",
                  delta="⚠️ HIGH" if latest['humidity_pct'] > 75 else None, delta_color="inverse")
        g2.metric("Shock",     f"{latest['shock_g']}g",
                  delta="⚠️ HIGH" if latest['shock_g'] > 2.0 else None, delta_color="inverse")
        g1.metric("Altitude",  f"{int(latest['altitude_m']):,}m")
        g2.metric("Customs",   latest["customs_status"].replace("_", " ").title())

        st.markdown("---")
        # Spoilage gauge
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=spoilage * 100,
            title={"text": "Spoilage Risk %", "font": {"color": "white", "size": 14}},
            delta={"reference": 30, "suffix": "%"},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "white"},
                "bar":  {"color": "#ef4444" if spoilage > 0.6 else "#f59e0b" if spoilage > 0.3 else "#22c55e"},
                "bgcolor": "#1a1a2e",
                "steps": [
                    {"range": [0, 30],  "color": "#0e1e14"},
                    {"range": [30, 60], "color": "#1e1a0e"},
                    {"range": [60, 100], "color": "#1e0e0e"},
                ],
                "threshold": {"line": {"color": "white", "width": 3}, "thickness": 0.8, "value": 60},
            },
            number={"suffix": "%", "font": {"color": "white"}},
        ))
        fig_gauge.update_layout(
            height=200, paper_bgcolor="#0f0f1a", font_color="white",
            margin=dict(l=20, r=20, t=40, b=10)
        )
        st.plotly_chart(fig_gauge, use_container_width=True)
    else:
        st.info("Awaiting first telemetry reading...")

st.divider()

# ─────────────────────────────── sensor charts ────────────────────────────────
st.markdown("### 📈 Sensor Timeline")
if telemetry:
    times = list(range(len(telemetry)))
    temps_all  = [r["temperature_c"] for r in telemetry]
    humid_all  = [r["humidity_pct"]  for r in telemetry]
    shock_all  = [r["shock_g"]       for r in telemetry]

    tc1, tc2, tc3 = st.columns(3)

    # Temperature
    with tc1:
        fig_t = go.Figure()
        fig_t.add_trace(go.Scatter(
            x=times, y=temps_all, mode="lines+markers",
            line=dict(color="#ef4444", width=2), marker=dict(size=4),
            name="Temp °C", fill="tozeroy", fillcolor="rgba(239,68,68,0.1)"
        ))
        fig_t.add_hline(y=8.0, line_dash="dash", line_color="#f59e0b", annotation_text="Max 8°C")
        fig_t.add_hline(y=2.0, line_dash="dash", line_color="#3b82f6", annotation_text="Min 2°C")
        fig_t.update_layout(
            title="🌡️ Temperature (°C)", height=200,
            paper_bgcolor="#0f0f1a", plot_bgcolor="#0a0a14",
            font_color="white", margin=dict(l=30, r=10, t=40, b=30),
            yaxis=dict(gridcolor="#1a1a2e"), xaxis=dict(gridcolor="#1a1a2e")
        )
        st.plotly_chart(fig_t, use_container_width=True)

    # Humidity
    with tc2:
        fig_h = go.Figure()
        fig_h.add_trace(go.Scatter(
            x=times, y=humid_all, mode="lines+markers",
            line=dict(color="#3b82f6", width=2), marker=dict(size=4),
            name="Humidity %", fill="tozeroy", fillcolor="rgba(59,130,246,0.1)"
        ))
        fig_h.add_hline(y=75.0, line_dash="dash", line_color="#f59e0b", annotation_text="Max 75%")
        fig_h.update_layout(
            title="💧 Humidity (%)", height=200,
            paper_bgcolor="#0f0f1a", plot_bgcolor="#0a0a14",
            font_color="white", margin=dict(l=30, r=10, t=40, b=30),
            yaxis=dict(gridcolor="#1a1a2e"), xaxis=dict(gridcolor="#1a1a2e")
        )
        st.plotly_chart(fig_h, use_container_width=True)

    # Shock
    with tc3:
        shock_colors = ["#ef4444" if s > 2.0 else "#8b5cf6" for s in shock_all]
        fig_s = go.Figure()
        fig_s.add_trace(go.Bar(
            x=times, y=shock_all, marker_color=shock_colors,
            name="Shock (g)"
        ))
        fig_s.add_hline(y=2.0, line_dash="dash", line_color="#f59e0b", annotation_text="Max 2g")
        fig_s.update_layout(
            title="💥 Shock (g-force)", height=200,
            paper_bgcolor="#0f0f1a", plot_bgcolor="#0a0a14",
            font_color="white", margin=dict(l=30, r=10, t=40, b=30),
            yaxis=dict(gridcolor="#1a1a2e"), xaxis=dict(gridcolor="#1a1a2e")
        )
        st.plotly_chart(fig_s, use_container_width=True)

st.divider()

# ─────────────────────────────── actions row ──────────────────────────────────
st.markdown("### 🎯 Cascading Actions Executed")
act_cols = st.columns(5)

route_rec = status.get("route_recommendation")
act_cols[0].markdown("**✈️ Reroute**")
if route_rec:
    act_cols[0].success(f"{route_rec['carrier']}")
    act_cols[0].caption(f"Risk {route_rec['risk_score']:.0%} · ${route_rec['cost_usd']:,}")
else:
    act_cols[0].caption("Not triggered")

act_cols[1].markdown("**🏥 Hospitals**")
notifs = status.get("notifications_sent", [])
if notifs:
    act_cols[1].success(f"{len(notifs)} notified")
    for n in notifs[:2]:
        act_cols[1].caption(n[:60])
else:
    act_cols[1].caption("Not triggered")

act_cols[2].markdown("**📦 Inventory**")
if inv_impact:
    act_cols[2].success(f"{inv_impact['expected_usable_doses']} usable doses")
    act_cols[2].caption(f"{inv_impact['total_appointments_at_risk']} appts at risk")
    act_cols[2].caption(f"Reorder: {inv_impact['reorder_urgency']}")
else:
    act_cols[2].caption("Not triggered")

act_cols[3].markdown("**❄️ Cold Storage**")
if status.get("cold_storage_booked"):
    act_cols[3].success(status.get("cold_storage_facility", "Booked"))
else:
    act_cols[3].caption("Not triggered")

act_cols[4].markdown("**📄 Insurance**")
claim_id = status.get("insurance_claim_id")
if claim_id:
    act_cols[4].success(claim_id)
else:
    act_cols[4].caption("Not triggered")

st.divider()

# ─────────────────────────────── inventory detail ─────────────────────────────
if inv_impact:
    with st.expander(f"📦 Inventory Forecast Detail — {inv_impact['destination']} ({inv_impact['total_appointments_at_risk']} appointments at risk)", expanded=False):
        col_sum, col_tbl = st.columns([1, 2])
        with col_sum:
            st.metric("Shipment Doses",    inv_impact["shipment_doses"])
            st.metric("Usable After Spoilage", inv_impact["expected_usable_doses"],
                      delta=f"-{inv_impact['doses_at_risk']}", delta_color="inverse")
            st.metric("Appointments at Risk", inv_impact["total_appointments_at_risk"])
            urgency_color = {"IMMEDIATE": "🔴", "HIGH": "🟠", "MONITOR": "🟡"}
            st.metric("Reorder Urgency", f"{urgency_color.get(inv_impact['reorder_urgency'], '⚪')} {inv_impact['reorder_urgency']}")
        with col_tbl:
            import pandas as pd
            rows = []
            for h in inv_impact["hospital_forecasts"]:
                rows.append({
                    "Hospital":          h["hospital"],
                    "Stock Now":         h["current_stock"],
                    "Delivery Doses":    h["expected_delivery_doses"],
                    "Post-Delivery":     h["projected_stock_after_delivery"],
                    "Appointments":      h["scheduled_appointments"],
                    "At Risk":           h["appointments_at_risk"],
                    "Reorder?":          "⚠️ YES" if h["reorder_recommended"] else "✅ No",
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ─────────────────────────────── anomaly list ─────────────────────────────────
if anomalies:
    with st.expander(f"⚠️ Detected Anomalies ({len(anomalies)})", expanded=severity in ("HIGH", "CRITICAL")):
        for a in anomalies:
            sev_icon = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🟠", "CRITICAL": "🔴"}.get(a["severity"], "⚪")
            st.markdown(f"{sev_icon} **{a['anomaly_type'].replace('_', ' ').title()}** — {a['description']}")
            st.caption(f"Z-score: {a.get('z_score', 'N/A')} · Raw: {a['raw_value']} · Threshold: {a['threshold_value']}")

# ─────────────────────────────── audit trail ──────────────────────────────────
st.markdown("### 📋 GDP/FDA Audit Trail (21 CFR Part 11)")
if audit:
    for entry in reversed(audit[-15:]):
        sev = entry.get("severity", "INFO")
        icon = {"LOW": "ℹ️", "INFO": "ℹ️", "MEDIUM": "⚠️", "HIGH": "🔶", "CRITICAL": "🚨"}.get(sev, "ℹ️")
        ts = entry.get("timestamp", "")[:19]
        with st.expander(f"{icon} **[{entry['agent_name']}]** {entry['action_type']} · {ts}"):
            col_d, col_r = st.columns([2, 3])
            col_d.markdown(f"**Action:**  \n{entry['action_detail']}")
            col_r.markdown(f"**Reasoning:**  \n{entry['reasoning'][:400]}")
            col_d.markdown(f"**GDP Compliant:** {'✅' if entry['gdp_compliant'] else '❌'}")
            col_r.markdown(f"**Severity:** {icon} {sev}")
else:
    st.caption("No audit entries yet — run a scenario to generate the GDP-compliant audit trail.")

# ─────────────────────────────── auto-refresh ─────────────────────────────────
if auto_refresh:
    time.sleep(REFRESH_INTERVAL)
    st.rerun()
