from _gen import *  # <AUTO GENERATED>
from functions.handoff import handoff


@func_description(
    'the user has rejected the proposed time slot. only call this if the user has not provided an alternative date or time, even something as vague as "can we do earlier in the afternoon"'
)
@func_latency_control(
    delay_before_responses_start=1,
    silence_after_each_response=5,
    delay_responses=[("just a moment please ...", 3)],
)
def go_to_slot_rejected(conv: Conversation, flow: Flow):
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

    flow.goto_step("Negotiate appointment time")
    return """The user changed their mind about the date/time for the scheduling of their appointment."
    """
