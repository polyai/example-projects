from _gen import *  # <AUTO GENERATED>


@func_description("Transition to step SMS_failed")
def go_to_sms_failed_1(conv: Conversation, flow: Flow):
    flow.goto_step("SMS failed")
