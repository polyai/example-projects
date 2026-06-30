from _gen import *  # <AUTO GENERATED>


@func_description(
    "To be called if the user asks to use a different number than the one they are calling from."
)
def phone_number_rejected(conv: Conversation, flow: Flow):
    flow.goto_step("Collect Alternative Phone Number")
