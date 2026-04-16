SPOILAGE_RATES = {
    "vaccine":   {"rate_per_degree_per_hour": 0.12},
    "biologics": {"rate_per_degree_per_hour": 0.20},
    "default":   {"rate_per_degree_per_hour": 0.08},
}


def calculate_spoilage_probability(cargo_type: str, temp_excursion_c: float, duration_minutes: float) -> float:
    rate = SPOILAGE_RATES.get(cargo_type.lower(), SPOILAGE_RATES["default"])["rate_per_degree_per_hour"]
    hours = duration_minutes / 60.0
    prob = min(1.0, temp_excursion_c * hours * rate)
    return round(prob, 3)
