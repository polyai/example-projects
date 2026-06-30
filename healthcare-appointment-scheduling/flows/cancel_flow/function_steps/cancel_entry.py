from datetime import datetime

import plog
from _gen import *  # <AUTO GENERATED>
from functions.appointment_selection import is_follow_up_appointment
from functions.load_cancel_upcoming_appointments import (
    load_cancel_upcoming_appointments_for_state,
)
from functions.nextgen_response_models import Appointment


def _format_date(raw: str) -> str:
    s = str(raw).strip() if raw else ""
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        try:
            return datetime.fromisoformat(s[:10]).strftime("%B %d, %Y").replace(" 0", " ")
        except ValueError:
            pass
    return s or "an unknown date"


def _list_upcoming_appointments(conv) -> str:
    raw = getattr(conv.state, "cancel_upcoming_appointments", None) or []
    appts = [Appointment.model_validate(x) for x in raw]
    eligible = [
        a
        for a in appts
        if is_follow_up_appointment(a) and a.appointment_date and a.is_rescheduled is not True
    ]
    eligible.sort(key=lambda a: str(a.appointment_date))
    if not eligible:
        return ""
    lines = [f"- {_format_date(a.appointment_date)}" for a in eligible]
    return "Their upcoming appointments:\n" + "\n".join(lines)


def cancel_entry(conv: Conversation, flow: Flow):
    """Cancel Flow entry: route based on how far through the cancel flow we are."""

    log_prefix = "[cancel_entry]: "
    pushback_done = getattr(conv.state, "cancel_pushback_done", False)
    triage_done = getattr(conv.state, "cancel_triage_done", False)
    plog.info(f"{log_prefix} cancel_pushback_done={pushback_done} cancel_triage_done={triage_done}")

    # Ensure appointments are loaded
    if not getattr(conv.state, "cancel_upcoming_appointments", None):
        identified = getattr(conv.state, "identified_patient", None)
        if isinstance(identified, dict) and identified.get("id"):
            plog.info(f"{log_prefix} loading cancel appointments (not preloaded)")
            load_cancel_upcoming_appointments_for_state(conv)

    if triage_done:
        plog.info(f"{log_prefix} triage already done, goto_step='Resolve Appointment'")
        flow.goto_step("Resolve Appointment", "Cancel triage already done")
        appt_list = _list_upcoming_appointments(conv)
        if appt_list:
            return {
                "content": (
                    f"{appt_list}\n\n"
                    "Read back the appointment date(s) and ask which one they want to cancel."
                )
            }
        return {"content": ("Ask the caller which appointment they would like to cancel.")}

    if pushback_done:
        caller_type_known = getattr(conv.state, "caller_is_case_manager", None) is not None
        if caller_type_known:
            plog.info(
                f"{log_prefix} pushback done (caller type known),"
                " goto_step='Triage Appointment Type'"
            )
            flow.goto_step("Triage Appointment Type", "Pushback done, proceeding to triage")
            return {
                "content": (
                    "Entering Cancel Flow. Review conversation history"
                    " to determine appointment type."
                )
            }
        plog.info(f"{log_prefix} pushback done, goto_step='Collect Caller Type'")
        flow.goto_step("Collect Caller Type", "Pushback done — collect caller type")
        return {"content": "Ask whether the caller is a patient or a case manager."}

    plog.info(f"{log_prefix} first entry, goto_step='Reschedule Pushback'")
    flow.goto_step("Reschedule Pushback", "Fresh cancel entry — offer reschedule first")
    return {"content": "Offer the caller the option to reschedule instead of cancel."}
