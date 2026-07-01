from _gen import *  # <AUTO GENERATED>
from flows.sms_flow.functions.SMS_failed import SMS_failed
from flows.sms_flow.functions.sms_sent_successfully import sms_sent_successfully


@func_description("User the number that the user is calling from to send the SMS")
def use_caller_number(conv: Conversation, flow: Flow):
    # if conv.caller_number:
    #     conv.state.sms_number = conv.caller_number

    # conv.state.sms_number = conv.state.phone_number
    # conv.state.sms_phone_number = "+13159969220" # just for testing
    # flow.goto_step("Send SMS")
    conv.state.sms_phone_number = conv.state.caller_number_cleanedup
    try:
        conv.send_sms_template(conv.state.sms_phone_number, conv.state.sms_id)
        return sms_sent_successfully(conv, flow)
    except Exception:
        return SMS_failed(conv, flow)
