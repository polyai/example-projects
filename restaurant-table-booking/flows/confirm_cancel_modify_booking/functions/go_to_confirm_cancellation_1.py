from _gen import *  # <AUTO GENERATED>


@func_description("Transition to step Confirm cancellation")
def go_to_confirm_cancellation_1(conv: Conversation, flow: Flow):
    flow.goto_step("Confirm cancellation")
