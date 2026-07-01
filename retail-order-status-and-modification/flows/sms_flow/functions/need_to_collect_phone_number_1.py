from _gen import *  # <AUTO GENERATED>


@func_description(
    "To be called if the user asks to use a different number than the one they are calling from."
)
def need_to_collect_phone_number_1(conv: Conversation, flow: Flow):
    flow.goto_step("Phone number collected")
