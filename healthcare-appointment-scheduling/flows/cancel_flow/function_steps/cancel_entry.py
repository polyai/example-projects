from datetime import datetime

from _gen import *  # <AUTO GENERATED>
from functions.load_cancel_upcoming_appointments import (
    load_cancel_upcoming_appointments_for_state,
)
from functions.nextgen_response_models import Appointment


def _format_date(raw: str) -> str:
    s = str(raw).strip() if raw else ""
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        try:
            return (
                datetime.fromisoformat(s[:10]).strftime("%B %d, %Y").replace(" 0", " ")
            )
        except ValueError:
            pass
    return s or "an unknown date"


def cancel_entry(conv: Conversation, flow: Flow):
    """Cancel Flow entry: load appointments and go to Resolve Appointment."""
    if not getattr(conv.state, "cancel_upcoming_appointments", None):
        identified = getattr(conv.state, "identified_patient", None)
        if isinstance(identified, dict) and identified.get("id"):
            load_cancel_upcoming_appointments_for_state(conv)

    flow.goto_step("Resolve Appointment")

    raw = getattr(conv.state, "cancel_upcoming_appointments", None) or []
    appts = [Appointment.model_validate(x) for x in raw]
    appts.sort(key=lambda a: str(a.appointment_date))
    if appts:
        lines = [f"- {_format_date(a.appointment_date)}" for a in appts]
        return {
            "content": (
                "Their upcoming appointments:\n"
                + "\n".join(lines)
                + "\n\nRead back the dates and ask which one they want to cancel."
            )
        }
    return {"content": "Ask the caller which appointment they would like to cancel."}
