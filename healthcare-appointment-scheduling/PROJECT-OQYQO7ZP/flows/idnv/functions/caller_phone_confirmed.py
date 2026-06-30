from _gen import *  # <AUTO GENERATED>


@func_description(
    "Called when the user confirms the number they're calling from is on their account."
)
def caller_phone_confirmed(conv: Conversation, flow: Flow):
    flow.goto_step("save_caller_phone_and_lookup")
    return {}
