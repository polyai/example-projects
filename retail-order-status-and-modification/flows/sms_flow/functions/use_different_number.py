from _gen import *  # <AUTO GENERATED>


@func_description("The caller wants to use a different phone number")
def use_different_number(conv: Conversation, flow: Flow):
    # Make sure your Flow function either transitions to a step or exits the flow
    flow.goto_step("Phone number collected")
