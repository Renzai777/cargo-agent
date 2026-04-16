GDP_THRESHOLDS = {
    "vaccine":   {"temp_min": 2.0, "temp_max": 8.0, "max_excursion_minutes": 120},
    "biologics": {"temp_min": -20.0, "temp_max": -15.0, "max_excursion_minutes": 30},
    "default":   {"temp_min": 2.0, "temp_max": 25.0, "max_excursion_minutes": 240},
}


def get_gdp_threshold(cargo_type: str) -> dict:
    return GDP_THRESHOLDS.get(cargo_type.lower(), GDP_THRESHOLDS["default"])


def is_gdp_compliant(cargo_type: str, temperature: float) -> bool:
    t = get_gdp_threshold(cargo_type)
    return t["temp_min"] <= temperature <= t["temp_max"]
