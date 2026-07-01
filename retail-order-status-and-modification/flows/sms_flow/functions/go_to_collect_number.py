from _gen import *  # <AUTO GENERATED>


@func_description("Transition to step Collect Number")
def go_to_collect_number(conv: Conversation, flow: Flow):
    flow.goto_step("Phone number collected")
