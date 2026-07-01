from _gen import *  # <AUTO GENERATED>
from flows.sms_flow.functions.SMS_failed import SMS_failed
from flows.sms_flow.functions.sms_sent_successfully import sms_sent_successfully


@func_description("Send SMS message")
@func_parameter("sms_phone_number", "The user's\xa0phone number to send the text to")
def send_sms(conv: Conversation, flow: Flow, sms_phone_number: str):
    try:
        conv.send_sms_template(conv.state.sms_phone_number, conv.state.sms_id)
        return sms_sent_successfully(conv, flow)
    except Exception as e:
        print(e)
        return SMS_failed(conv, flow)
