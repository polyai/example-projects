from _gen import *  # <AUTO GENERATED>
from functions.handoff import handoff
from functions.routes_api_call import update_appointment


@func_description("reschedule the user's appointment")
@func_latency_control(
    delay_before_responses_start=3,
    silence_after_each_response=4,
    delay_responses=[
        ("ok, let me just get that rescheduled for you...", 3),
        ("just another second...", 2),
        ("bear with me...", 2),
    ],
)
def reschedule_appointment(conv: Conversation, flow: Flow):
    slot = conv.state.potential_slot
    if slot is None:
        raise ValueError("potential_slot must be set before calling this function")
    appointment = conv.state.appointment
    if appointment is None:
        raise ValueError("appointment must be set before calling this function")

    try:
        if update_appointment(
            conv,
            appointment["appointmentID"],
            appointment["routeID"],
            appointment["date"],
            slot["spotID"],
            slot.get("start"),
            slot.get("end"),
        ):  # returns success status
            conv.state.appointment = None  # rescheduled appointment can be retrieved again separately if needed
            pass
        else:
            handoff_reason = "RESCHEDULE_APPOINTMENT_FAIL"
            return handoff(
                conv,
                handoff_reason,
                "I'm afraid I am facing some technical difficulties doing this at this moment, let me put you through to someone who can help, just a moment please!",
                "CUSTOMER_CARE",
            )
    except Exception:
        handoff_reason = "API_TIMEOUT" if conv.state.api_timeout else "API_ERROR"
        return handoff(
            conv,
            handoff_reason,
            "I'm afraid I am facing some technical difficulties doing this at this moment, let me put you through to someone who can help, just a moment please!",
            "CUSTOMER_CARE",
        )

    conv.write_metric("MODIFY_APPOINTMENT_FLOW_SUCCESSFUL", None)
    conv.exit_flow()
    timeframe_readback = conv.state.new_appointment_timeframe_readback or ""
    return f"""You have successfully rescheduled the user's appointment. Tell the user: "Okay, your new appointment is set for {slot["date"]} {timeframe_readback}. We'll make sure to notify you by text about 30 minutes before we get there." remembering to say the date and time in natural English
    """
