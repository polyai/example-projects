from datetime import datetime

import plog
from _gen import *  # <AUTO GENERATED>
from functions.appointment_selection import is_follow_up_appointment
from functions.handoff import handoff
from functions.nextgen_response_models import Appointment


def _readable_date(raw_dt: object) -> str:
    """'2026-03-28T00:00:00' -> 'March 28, 2026'."""
    s = str(raw_dt).strip() if raw_dt else ""
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        try:
            return datetime.fromisoformat(s[:10]).strftime("%B %d, %Y").replace(" 0", " ")
        except ValueError:
            pass
    return s or "an unknown date"


@func_description(
    "Find the caller's next upcoming eligible (follow-up) appointment and return its readable date so the agent can read it back and ask if that is the one they want to reschedule."
)
def suggest_next_reschedule_appointment(conv: Conversation, flow: Flow) -> dict:
    log_prefix = "[suggest_next_reschedule_appointment]: "

    raw = getattr(conv.state, "reschedule_upcoming_appointments", None) or []
    appointments = [Appointment.model_validate(x) for x in raw]
    plog.info(f"{log_prefix} reschedule_upcoming_appointments count={len(raw)}")

    eligible = [
        a
        for a in appointments
        if is_follow_up_appointment(a) and a.appointment_date and a.is_rescheduled is not True
    ]
    eligible.sort(key=lambda a: str(a.appointment_date))
    plog.info(f"{log_prefix} eligible_follow_up_count={len(eligible)}")

    if not eligible:
        plog.info(f"{log_prefix} no eligible appointments; handing off")
        conv.write_metric("RESCHEDULE_DATE_UNKNOWN_NO_ELIGIBLE_APPT")
        return handoff(
            conv,
            reason="RESCHEDULING_DATE_UNAVAILABLE",
            utterance="Please hold while I transfer you to someone who can help.",
        )

    next_appt = eligible[0]
    readable = _readable_date(next_appt.appointment_date)
    plog.info(
        f"{log_prefix} next_eligible_appointment_date='{str(next_appt.appointment_date)[:10]}'",
        is_pii=True,
    )
    conv.write_metric("RESCHEDULE_DATE_UNKNOWN_SUGGESTED_NEXT_APPT")

    is_cm = getattr(conv.state, "caller_is_case_manager", False)
    if is_cm:
        return {
            "content": (
                f"The patient's next upcoming eligible follow-up visit is on {readable}. "
                f"Say something like: 'I can see the patient's next visit is on {readable} — is that "
                f"the one they're looking to reschedule?' Keep it natural and brief."
            )
        }
    return {
        "content": (
            f"The patient's next upcoming eligible follow-up visit is on {readable}. "
            f"Say something like: 'I can see your next visit is on {readable} — is that "
            f"the one you're looking to reschedule?' Keep it natural and brief."
        )
    }
