from _gen import *  # <AUTO GENERATED>


@func_description(
    "Call if user rejects a standard booking/reservation for the slot you offered them"
)
def standard_booking_rejected(conv: Conversation, flow: Flow):
    # Make sure your Flow function either transitions to a step or exits the flow
    flow.goto_step(
        "Selected experience not available, no alternative availability at requested time"
    )
    return "User doesn't want to make a standard booking, ask them if you can check another date or time."
