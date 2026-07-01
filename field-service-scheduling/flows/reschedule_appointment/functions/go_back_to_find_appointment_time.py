from _gen import *  # <AUTO GENERATED>
from functions.handoff import handoff


@func_description("Transition to step Negotiate modified visit")
@func_latency_control(
    delay_before_responses_start=1,
    silence_after_each_response=0,
    delay_responses=[("one moment please", 3)],
)
def go_back_to_find_appointment_time(conv: Conversation, flow: Flow):
    if not conv.state.slots_rejected:
        conv.state.slots_rejected = 1
    else:
        conv.state.slots_rejected += 1
        if conv.state.slots_rejected > 2:
            return handoff(
                conv,
                "OFFERED_APPOINTMENT_SLOT_REJECTED",
                "Let me put you through to someone who can help, just a moment please!",
                "CUSTOMER_CARE",
            )

    flow.goto_step("Negotiate modified visit")
    return """The user changed their mind about the date/time for the rescheduling of their appointment. Tell the user: "No problem! When would be a good time to reschedule that appointment for?"
    """
