MOCK_ROUTES = {
    "SHP-TEST-001": {"eta_minutes": 480, "origin": "New York", "destination": "Nairobi"},
    "SHP-DEMO-001": {"eta_minutes": 320, "origin": "New York", "destination": "Nairobi"},
}


def get_route_eta(shipment_id: str) -> dict:
    route = MOCK_ROUTES.get(shipment_id, {"eta_minutes": 400, "origin": "Unknown", "destination": "Unknown"})
    return {
        "shipment_id": shipment_id,
        "remaining_minutes": route["eta_minutes"],
        "origin": route["origin"],
        "destination": route["destination"],
    }
