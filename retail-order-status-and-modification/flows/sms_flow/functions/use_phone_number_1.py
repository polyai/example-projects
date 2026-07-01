from _gen import *  # <AUTO GENERATED>


@func_description("Use the number that the user is calling from")
def use_phone_number_1(conv: Conversation, flow: Flow):
    conv.state.sms_phone_number = conv.caller_number
    flow.goto_step("Send SMS")
