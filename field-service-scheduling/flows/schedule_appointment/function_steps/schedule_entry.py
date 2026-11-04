from _gen import *  # <AUTO GENERATED>
from flows.schedule_appointment.functions.update_visit_request import request_state
from functions import idnv


def schedule_entry(conv: Conversation, flow: Flow):
    """Entry gate: unverified callers go to verify_caller and come back here."""
    conv.state.task = "schedule"
    gate = idnv.require(conv, "schedule_appointment")
    if gate:
        return gate

    conv.write_metric("MAKE_APPOINTMENT_FLOW_INITIATED", write_once=True)
    flow.goto_step("Schedule Visit", "caller verified")
    return (
        "First, if what they've described is urgent (water pouring or flooding, no heat, no AC, a "
        "gas leak that's been made safe, or they say it's an emergency or can't wait) and you "
        "haven't yet made the urgent offer, make it now: \"That sounds urgent. I can put you "
        "through to our emergency team to get someone out today, or book a regular visit from "
        "tomorrow. Which would you prefer?\" (after a gas leak that's been dealt with, start with "
        "\"Oh, I'm glad you're safe.\"). A drip, a jam or a leaking appliance isn't urgent. "
        "Otherwise help the caller book a visit. If they've already said what the problem is, call "
        "update_visit_request with it now; if they've said when suits (today, a day, the earliest), "
        "call find_visit_time with it as well, with day_said in their words ('today'), instead "
        "of asking when. Never ask again for anything they've said, and don't ask for a name, an "
        f"address or a contact number.\n\n{request_state(conv)}"
    )
