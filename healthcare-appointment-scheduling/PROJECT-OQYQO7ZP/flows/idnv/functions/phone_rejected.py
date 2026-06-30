from _gen import *  # <AUTO GENERATED>


@func_description("Called when the user says the phone number read back to them is wrong.")
def phone_rejected(conv: Conversation, flow: Flow):
    flow.goto_step("retry_collect_phone")
    return {}
