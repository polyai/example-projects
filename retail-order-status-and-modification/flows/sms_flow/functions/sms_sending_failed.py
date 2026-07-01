from _gen import *  # <AUTO GENERATED>
from functions.utterances import utterance


@func_description("Exit the SMS flow")
def sms_sending_failed(conv: Conversation, flow: Flow):
    return {
        "utterance": utterance(conv, "sms_anything_else"),
        "transition": {"exit_flow": True},
    }
