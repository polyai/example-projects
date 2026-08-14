"""Called when the caller picks one of the ambiguous same-day appointments."""

from datetime import datetime

import plog

from _gen import *  # <AUTO GENERATED>
from functions.appointment_selection import is_follow_up_appointment
from functions.handoff import handoff
from functions.nextgen_response_models import Appointment


def _readable_date(raw_dt: object) -> str:
    s = str(raw_dt).strip() if raw_dt else ""
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        try:
            return (
                datetime.fromisoformat(s[:10]).strftime("%B %d, %Y").replace(" 0", " ")
            )
        except ValueError:
            pass
    return s or "an unknown date"


@func_description(
    "Called when the caller selects which same-day appointment they want to cancel. selection is the 1-based index of the appointment they chose."
)
@func_parameter(
    "selection",
    "Which appointment the caller chose: 1 for the first, 2 for the second, etc.",
)
def disambiguation_selection_made(conv: Conversation, flow: Flow, selection: int):
    log_prefix = "[disambiguation_selection_made]: "
    plog.info(f"{log_prefix} selection={selection}")

    raw = getattr(conv.state, "cancel_ambiguous_matches", None) or []
    matches = [Appointment.model_validate(x) for x in raw]

    idx = int(selection) - 1
    if idx < 0 or idx >= len(matches):
        plog.info(f"{log_prefix} invalid index {idx}; falling back to first match")
        idx = 0

    chosen = matches[idx]

    if not is_follow_up_appointment(chosen):
        conv.write_metric("CANCEL_FLOW_NON_FOLLOW_UP", True)
        conv.write_metric("CANCEL_OOS", True)
        return handoff(
            conv,
            reason="CANCEL_NON_FOLLOW_UP",
            utterance="That type of visit can't be cancelled on this line. I'll transfer you to someone who can help.",
        )

    if chosen.is_rescheduled is True:
        plog.info(f"{log_prefix} appointment already rescheduled; exiting flow")
        conv.write_metric("CANCEL_FLOW_ALREADY_RESCHEDULED", True)
        conv.state.pending_transfer_reason = "CANCEL_ALREADY_RESCHEDULED"
        conv.exit_flow()
        return {
            "content": (
                "This appointment has already been rescheduled, so it can't be cancelled "
                "through this line. Offer to transfer the caller to someone who can help, "
                "but first ask if there's anything else they need."
            )
        }

    appt_id = chosen.appointment_id or chosen.id
    if not appt_id:
        plog.info(f"{log_prefix} matched appointment missing id; exiting")
        conv.log.error("Cancel flow: disambiguation matched appointment has no id")
        conv.exit_flow()
        return {
            "utterance": "Something went wrong matching that appointment. Please try again.",
        }

    conv.state.cancel_target_appointment_id = str(appt_id)
    conv.log.info(
        "Cancel flow: disambiguated follow-up appointment",
        appointment_id_last4=str(appt_id)[-4:] if len(str(appt_id)) >= 4 else "****",
    )

    flow.goto_step("Confirm Cancellation")
    when = _readable_date(chosen.appointment_date)
    return {
        "utterance": (
            f"Got it. We can cancel that visit on {when}. Do you want to go ahead and cancel that?"
        )
    }
