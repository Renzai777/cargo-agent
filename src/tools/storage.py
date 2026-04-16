MOCK_FACILITIES = [
    {"id": "CSF-FRA-001", "name": "Frankfurt ColdHub", "capacity_kg": 500, "temp_range": "2-8°C", "distance_km": 15},
    {"id": "CSF-FRA-002", "name": "Rhine Cold Storage", "capacity_kg": 300, "temp_range": "2-8°C", "distance_km": 22},
]


def find_cold_storage(location: str, cargo_type: str) -> dict:
    return {"facilities": MOCK_FACILITIES, "location": location}


def book_cold_storage(facility_id: str, shipment_id: str, duration_hours: int) -> dict:
    facility = next((f for f in MOCK_FACILITIES if f["id"] == facility_id), MOCK_FACILITIES[0])
    return {
        "status": "booked",
        "facility": facility["name"],
        "shipment_id": shipment_id,
        "duration_hours": duration_hours,
    }
