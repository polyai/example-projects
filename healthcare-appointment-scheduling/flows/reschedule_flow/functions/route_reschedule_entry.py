from _gen import *  # <AUTO GENERATED>


@func_description("Entry routing for the Reschedule Flow.")
def route_reschedule_entry(conv: Conversation, flow: Flow) -> dict:
    flow.goto_step("Resolve Appointment")
    return {
        "content": "Ask the caller which appointment they would like to reschedule."
    }
