from _gen import *  # <AUTO GENERATED>


@func_description("Called when the caller confirms they want to cancel.")
def caller_confirmed_cancel(conv: Conversation, flow: Flow) -> dict:
    conv.write_metric("CANCEL_CONFIRMED", True)
    flow.goto_step("Resolve Appointment")
    return {"content": "Ask which appointment they would like to cancel."}
