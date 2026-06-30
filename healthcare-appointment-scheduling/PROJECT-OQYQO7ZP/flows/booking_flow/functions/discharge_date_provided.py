"""Called when the caller provides their discharge date; validates the discharge window and asks for facility name."""

from datetime import datetime, timedelta

import plog
from _gen import *  # <AUTO GENERATED>
from functions.handoff import handoff

_DISCHARGE_WINDOW_DAYS = {
    "hospital_follow_up": 7,
    "er_follow_up": 14,
}


@func_description(
    "Called when the caller provides their discharge date from the hospital or ER. Stores the date and routes to facility name collection."
)
@func_parameter(
    "discharge_date", "The caller's discharge date in YYYY-MM-DD format (e.g. '2026-03-25')."
)
def discharge_date_provided(conv: Conversation, flow: Flow, discharge_date: str):
    """Store discharge date, check if the discharge window has passed, and ask for facility name."""
    log_prefix = "[discharge_date_provided.discharge_date_provided]: "
    plog.info(f"{log_prefix} discharge_date='{discharge_date}'", is_pii=True)

    conv.state.booking_discharge_date = discharge_date
    conv.write_metric("BOOKING_FLOW_DISCHARGE_DATE", discharge_date)

    # Check if the discharge window has already expired
    appt_type = getattr(conv.state, "booking_appointment_type", None) or ""
    window_days = _DISCHARGE_WINDOW_DAYS.get(appt_type, 14)
    try:
        parsed_date = datetime.strptime(discharge_date, "%Y-%m-%d").date()
        cutoff_date = parsed_date + timedelta(days=window_days)
        today = datetime.now().date()
        plog.info(
            f"{log_prefix} window_days={window_days} cutoff_date='{cutoff_date}' today='{today}'",
            is_pii=True,
        )
        if today > cutoff_date:
            plog.info(f"{log_prefix} discharge window has passed; handing off")
            conv.write_metric("BOOKING_FLOW_DISCHARGE_WINDOW_EXPIRED")
            return handoff(
                conv,
                reason="BOOKING_DISCHARGE_WINDOW_EXPIRED",
                utterance=(
                    f"It sounds like your discharge was more than {window_days} days ago. "
                    "I'll need to transfer you to someone who can help get that appointment set up."
                ),
            )
    except (ValueError, TypeError) as e:
        plog.info(f"{log_prefix} could not parse discharge_date for window check: {e}", is_pii=True)

    facility_label = getattr(conv.state, "booking_facility_type_label", None) or "facility"
    flow.goto_step("Collect Facility Name")
    return {"utterance": f"Got it. And what was the name of the {facility_label}?"}
