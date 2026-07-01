from _gen import *  # <AUTO GENERATED>


@func_description("Transition to step Send SMS")
def go_to_send_sms(conv: Conversation, flow: Flow):
    flow.goto_step("Send SMS")
