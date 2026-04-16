"""
Pre-scripted demo responses for DEMO_MODE=true.

When DEMO_MODE=true in .env, no real API calls are made.
All Claude agent responses are replaced with realistic pre-written content
so the full pipeline runs without an Anthropic API key.
"""

ANOMALY_DEMO = {
    "severity": "CRITICAL",
    "anomaly_type": "temperature_excursion",
    "description": (
        "Refrigeration unit failure detected. Temperature has risen to 14.2°C — "
        "6.2°C above the 8°C GDP cold-chain ceiling for mRNA vaccines. "
        "At current rate, product integrity will be compromised within 23 minutes."
    ),
}

RISK_DEMO = {
    "spoilage_probability": 0.73,
    "delay_risk": 0.61,
    "severity": "CRITICAL",
    "reasoning": (
        "Tool output: calculate_spoilage_probability → 0.73 (vaccine, +6.2°C excursion, 18 min duration). "
        "Tool output: get_route_eta → 214 minutes remaining to Nairobi. "
        "At 73% spoilage probability with 214 minutes remaining and no cold-chain recovery options "
        "on the current route, this is a CRITICAL incident. The Arrhenius degradation model for "
        "mRNA vaccines predicts irreversible denaturation within 30 minutes at current temperature. "
        "Delay risk is HIGH (61%) due to Frankfurt airspace congestion adding estimated 55-minute hold."
    ),
}

ORCHESTRATOR_THINKING_DEMO = """
Let me carefully reason through this incident before deciding on interventions.

SITUATION:
- Shipment: COVID-19 mRNA Vaccine, 500 doses, NYC → Frankfurt → Nairobi
- Temperature: 14.2°C (threshold: 8°C) — 6.2°C excursion
- Spoilage probability: 73%
- Delay risk: 61%
- Predicted breach of complete spoilage: ~23 minutes

COST-BENEFIT ANALYSIS:

Option 1: REROUTE
- Cost: ~$45,000 carrier change fee + $12,000 logistics
- Benefit: Reduces remaining transit time by 3h if routed via Lufthansa cargo
- Spoilage risk reduction: ~40% if rerouted within 15 min
- Verdict: REQUIRED. At $57k vs. $2.1M vaccine loss, this is non-negotiable.

Option 2: COLD_STORAGE
- Cost: ~$8,000 Frankfurt Airport facility booking
- Benefit: Immediately stops temperature damage while rerouting is arranged
- Verdict: REQUIRED. Should be booked in parallel with rerouting.

Option 3: NOTIFY_HOSPITALS
- GDP Article 9.2 mandates notification when breach probability > 50%
- 150 patient appointments at Kenyatta National Hospital are at risk
- Regulatory obligation: MANDATORY regardless of intervention outcome
- Verdict: REQUIRED by law and ethics.

Option 4: FILE_INSURANCE
- Spoilage probability 73% exceeds our 70% threshold for claim initiation
- Better to file now while timeline documentation is fresh
- Verdict: REQUIRED.

Option 5: CUSTOMS_ESCALATE
- No customs hold detected on current telemetry
- Verdict: NOT REQUIRED at this time.

CONCLUSION: Activate REROUTE, COLD_STORAGE, NOTIFY_HOSPITALS, FILE_INSURANCE in parallel.
Time is critical — every minute of delay increases spoilage probability by ~2%.
"""

ORCHESTRATOR_RESPONSE_DEMO = """Based on the incident data, I am activating the following interventions immediately:

**REROUTE** — Current route via Ethiopian Airlines must be changed. Recommend Lufthansa Cargo LH8142
departing Frankfurt in 47 minutes. This reduces remaining transit time by 3 hours and connects
to a refrigerated hold unit confirmed at -20°C.

**COLD_STORAGE** — Emergency cold storage must be booked at Frankfurt Airport Cargo Center,
Facility C-7 (confirmed available, -20°C capacity for 600 units). This arrests temperature
damage immediately while rerouting is coordinated.

**NOTIFY_HOSPITALS** — GDP Article 9.2 mandates immediate notification. 150 patient appointments
at Kenyatta National Hospital and 40 at Aga Khan University Hospital are at risk. Hospitals must
initiate contingency protocols and contact alternate suppliers.

**FILE_INSURANCE** — Spoilage probability of 73% exceeds the 70% threshold for insurance claim
initiation. Filing now preserves the timeline documentation and sensor evidence while the incident
is active.

Rationale: At $57,000 total intervention cost versus $2.1M in vaccine replacement cost plus
190 patient appointment disruptions, all four actions are economically and regulatorily justified.
Intervention window is approximately 23 minutes before irreversible product loss.
"""
