from _gen import *  # <AUTO GENERATED>


@func_description("Transition to step Collect Phone Number")
def no_number_given(conv: Conversation, flow: Flow):
    flow.goto_step("Phone number collected")
