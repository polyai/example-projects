from _gen import *  # <AUTO GENERATED>


@func_description("Transition to step Collect associated phone number")
def go_to_collect_associated_phone_number(conv: Conversation, flow: Flow):
    flow.goto_step("Collect associated phone number")
