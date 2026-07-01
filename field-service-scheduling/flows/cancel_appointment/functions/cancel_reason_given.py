from _gen import *  # <AUTO GENERATED>
from functions.handoff import handoff
from functions.routes_api_call import cancel_appointment


@func_description("Collect and save the reason for cancellation")
@func_parameter(
    "cancel_reason",
    "Okay, and just for our records, would you mind telling me briefly why you're cancelling? Default to 'N/A' if the value cannot be extracted.",
)
@func_latency_control(
    delay_before_responses_start=0,
    silence_after_each_response=7,
    delay_responses=[("Alrighty, just submitting that cancellation here...", 3)],
)
def cancel_reason_given(conv: Conversation, flow: Flow, cancel_reason: str):
    appointment = conv.state.appointment
    if appointment is None:
        raise ValueError("appointment must be set before calling this function")
    try:
        if cancel_appointment(
            conv, appointment["appointmentID"], f'From customer: "{cancel_reason}"'
        ):  # returns success status
            conv.state.appointment = None
            pass
        else:
            handoff_reason = "CANCEL_APPOINTMENT_FAIL"
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

    conv.write_metric("CANCEL_APPOINTMENT_FLOW_SUCCESSFUL", None)
    conv.exit_flow()
    return """You have successfully cancelled the user's appointment. Tell the user: "Okay, you're all set. That appointment is cancelled."
    """
