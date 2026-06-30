from _gen import *  # <AUTO GENERATED>


@func_description(
    "Called when the user refuses to provide a phone number or says they don't have one."
)
def phone_collection_refused(conv: Conversation, flow: Flow):
    flow.goto_step("phone_collection_failed")
    return {}
