def send_hospital_alert(hospital_name: str, message: str, severity: str) -> dict:
    return {"status": "sent", "hospital": hospital_name, "message": message, "severity": severity}


def reschedule_appointment(appointment_id: str, reason: str) -> dict:
    return {"status": "rescheduled", "appointment_id": appointment_id, "reason": reason}
