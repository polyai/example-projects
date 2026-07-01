from _gen import *  # <AUTO GENERATED>


@func_description("Transition to step Collect appointment details")
def go_to_collect_appointment_details(conv: Conversation, flow: Flow):
    flow.goto_step("Collect appointment details")
