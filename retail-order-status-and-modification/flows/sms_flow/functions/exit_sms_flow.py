from _gen import *  # <AUTO GENERATED>


@func_description("Exit the SMS flow flow")
def exit_sms_flow(conv: Conversation, flow: Flow):
    conv.exit_flow()
