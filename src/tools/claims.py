import random
import string
from datetime import datetime


def file_insurance_claim(shipment_id: str, damage_description: str, estimated_value_usd: float) -> dict:
    claim_id = "CLM-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return {
        "claim_id": claim_id,
        "shipment_id": shipment_id,
        "status": "filed",
        "estimated_value_usd": estimated_value_usd,
        "filed_at": datetime.utcnow().isoformat(),
    }
