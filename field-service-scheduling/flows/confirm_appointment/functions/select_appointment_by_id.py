from _gen import *  # <AUTO GENERATED>
from functions.handoff import handoff
from functions.utils import get_prompt_for_appointment_timeframe_readback


@func_description("select the appointment based on the given appointment type or time")
@func_parameter("appointment_id", "the ID of the appointment")
def select_appointment_by_id(conv: Conversation, flow: Flow, appointment_id: str):
    for appointment in conv.state.appointments_on_date:
        if appointment["appointmentID"] == appointment_id:
            conv.state.appointment = appointment
            appointment_timeframe_readback_prompt = (
                get_prompt_for_appointment_timeframe_readback(
                    appointment, conv.state.call_intent
                )
            )
            flow.goto_step("Confirm appointment")
            return f"""You have found the user's appointment. Say: "So I see a {appointment["serviceType"]} appointment here for {appointment["date"]} {appointment_timeframe_readback_prompt}"
            """
    return handoff(
        conv,
        "NO_APPOINTMENTS_FOUND_ON_GIVEN_DATE",
        "Let me transfer you to a colleague who can help with this. One moment please.",
        "CUSTOMER_CARE",
    )
