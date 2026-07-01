from _gen import *  # <AUTO GENERATED>


@func_description("Transition to step Negotiate modified visit")
def go_to_negotiate_modified_visit(conv: Conversation, flow: Flow):
    flow.goto_step("Negotiate modified visit")
