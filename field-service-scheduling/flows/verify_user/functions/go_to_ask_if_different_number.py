from _gen import *  # <AUTO GENERATED>


@func_description("Transition to step Ask if account under different number")
def go_to_ask_if_different_number(conv: Conversation, flow: Flow):
    flow.goto_step("Ask if account under different number")
