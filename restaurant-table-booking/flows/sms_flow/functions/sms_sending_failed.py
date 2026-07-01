from _gen import *  # <AUTO GENERATED>
from functions.try_transfer_call import try_transfer_call


@func_description("Transition to step SMS sending failed")
def sms_sending_failed(conv: Conversation, flow: Flow):
    conv.write_metric("SMS_FAILED")
    if conv.state.sms_failed_once:
        return try_transfer_call(
            conv,
            "CANNOT_SEND_SMS",
            "Ok, let me transfer you to someone that can help. One second",
            "default",
        )
    flow.goto_step("SMS sending failed")
    conv.state.sms_failed_once = True
    return {
        "utterance": "Looks like something went wrong sending the SMS. Could you please try giving me your mobile phone number again?"
    }
