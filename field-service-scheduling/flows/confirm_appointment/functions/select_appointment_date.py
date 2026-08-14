from _gen import *  # <AUTO GENERATED>
from datetime import datetime

from functions.handoff import handoff
from functions.utils import get_prompt_for_appointment_timeframe_readback


@func_description(
    "try to narrow down the appointment based on the date the user has given"
)
@func_parameter(
    "appointment_date",
    'Selected appointment date. Should be converted to  year-month-day format (e.g. 2000-12-26). Use context from the appointment dates you are seeing - if the user says "the next one" or something similar, use the date of the soonest appointment, taking into account the current date',
)
def select_appointment_date(conv: Conversation, flow: Flow, appointment_date: str):
    # Input validation
    try:
        datetime.strptime(appointment_date, "%Y-%m-%d")
    except ValueError:
        return """The date you provided was in the wrong format. If you know the date requested by the user, please try calling
      this function again using the following format: YYYY-MM-DD. Otherwise, ask the user what date is the appointment on."""

    matched_appointments = [
        a for a in conv.state.appointments if a["date"] == appointment_date
    ]

    if len(matched_appointments) == 0:
        if not conv.state.collect_appointment_date_attempted:
            conv.state.collect_appointment_date_attempted = True
            return "Say that the provided appointment date did not match any records and ask the user to try again"
        else:
            return handoff(
                conv,
                "NO_APPOINTMENTS_FOUND_ON_GIVEN_DATE",
                "Let me transfer you to a colleague who can help with this. One moment please.",
                "CUSTOMER_CARE",
            )
    elif len(matched_appointments) > 1:
        flow.goto_step("Several appointments on same day")
        conv.state.appointment_date = appointment_date
        conv.state.appointments_on_date = matched_appointments
        return "You have found several upcoming appointments on the same day."

    conv.write_metric("MULTIPLE_APPOINTMENTS_DISAMBIGUATED_WITH_DATE", None)
    conv.state.appointments = matched_appointments

    appointment = matched_appointments[0]
    conv.state.appointment = appointment
    appointment_timeframe_readback_prompt = (
        get_prompt_for_appointment_timeframe_readback(
            appointment, conv.state.call_intent
        )
    )
    flow.goto_step("Confirm appointment")
    return f"""You have found the user's appointment. Say: "So I see a {appointment["serviceType"]} appointment here for {appointment["date"]} {appointment_timeframe_readback_prompt}"
    """
