from _gen import *  # <AUTO GENERATED>
from functions.utterances import utterance


@func_description("Check if we need to collect the user phone number.")
def check_user_phone_number(conv: Conversation, flow: Flow):
    if conv.state.sent_sms_to_number:
        flow.goto_step("Send SMS")
        return "You already collected a number once, no need to collect it again."
    else:
        return {
            "utterance": utterance(conv, "sms_ask_this_number"),
            "transition": {
                "goto_flow": "SMS flow",
                "goto_step": "Ask this number",
            },
        }
