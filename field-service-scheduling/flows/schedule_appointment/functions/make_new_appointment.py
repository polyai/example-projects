from _gen import *  # <AUTO GENERATED>
from functions.handoff import handoff
from functions.routes_api_call import create_appointment
from functions.utils import dates_in_same_month


@func_description("make a new appointment for the user")
@func_parameter(
    "additional_notes",
    'Any additional notes, concerns, or requests the user has for their appointment. Set to "NA" if nothing additional',
)
@func_latency_control(
    delay_before_responses_start=1,
    silence_after_each_response=3,
    delay_responses=[
        ("okay, I'm booking that in for you ... ", 3),
        ("just a moment ...", 3),
        ("one second ", 3),
    ],
)
def make_new_appointment(conv: Conversation, flow: Flow, additional_notes: str):
    slot = conv.state.potential_slot
    if slot is None:
        raise ValueError("potential_slot must be set before calling this function")
    subscription = conv.state.subscription
    if subscription is None:
        raise ValueError("subscription must be set before calling this function")

    conv.state.due_for_regular_service = dates_in_same_month(
        slot["date"], subscription["nextService"]
    )  # https://poly-ai.atlassian.net/browse/UTIL-2618

    if additional_notes != "NA":
        conv.state.additional_notes = additional_notes

    try:
        if create_appointment(
            conv, slot["spotID"], slot.get("start"), slot.get("end")
        ):  # returns success status
            pass
        else:
            handoff_reason = "SCHEDULE_APPOINTMENT_FAIL"
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

    conv.write_metric("MAKE_APPOINTMENT_FLOW_SUCCESSFUL", None)
    conv.exit_flow()
    timeframe_readback = conv.state.new_appointment_timeframe_readback or ""
    return f"""You have successfully scheduled the user's appointment. Tell the user: "Alrighty, you're all set for {slot["date"]} {timeframe_readback}. We'll be servicing {conv.state.service_names} at {conv.state.service_location}.  We'll make sure to notify you by text about 30 minutes before we get there." remembering to say the date and time in natural English
    """
