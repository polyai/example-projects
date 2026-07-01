from _gen import *  # <AUTO GENERATED>


@func_description(
    "Call this function only when the user want to restart the verification process with a different phone number."
)
def use_different_phone_number(conv: Conversation, flow: Flow):
    flow.goto_step("Collect phone number")
