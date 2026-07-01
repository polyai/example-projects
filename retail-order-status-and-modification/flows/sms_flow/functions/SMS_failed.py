from _gen import *  # <AUTO GENERATED>
from functions.utterances import utterance


@func_description("Sending the SMS failed")
def SMS_failed(conv: Conversation, flow: Flow):
    conv.write_metric("SMS_FAILED")
    if conv.state.coming_from_WISMO:
        return {
            "utterance": utterance(conv, "sms_failed_text"),
            "transition": {"goto_flow": "SMS flow", "goto_step": "WISMO check - sending failed"},
        }
    else:
        return {
            "utterance": utterance(conv, "sms_failed_text"),
            "transition": {"goto_flow": "SMS flow", "goto_step": "SMS failed"},
        }
