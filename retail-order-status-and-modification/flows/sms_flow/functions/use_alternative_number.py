from _gen import *  # <AUTO GENERATED>


@func_description("user wants to use a different number to the one they're calling from")
def use_alternative_number(conv: Conversation, flow: Flow):
    flow.goto_step("Phone number collected")
