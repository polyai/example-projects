from _gen import *  # <AUTO GENERATED>


@func_description("Enter the SMS flow flow")
def start_sms_flow(conv: Conversation):
    conv.goto_flow("SMS flow")
