import re

from _gen import *  # <AUTO GENERATED>
from functions.utterances import utterance


def is_valid_US_number(phone_number: str):
    """
    Validates if a phone_number is a valid US number
    """
    if not phone_number:
        return False
    # Regex pattern to match US numbers
    pattern = r"^(?:\+1|1)?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}$"

    is_match = re.match(pattern, phone_number)
    return is_match


@func_description("Start sending the tracking link to the user")
def start_sending_sms(conv: Conversation, flow: Flow):
    conv.state.coming_from_WISMO = True

    # set initial sms value
    # conv.state.tracking_sms = conv.state.item_urls.pop()

    # # reset meaning of caller number
    # if conv.caller_number:
    #   conv.state.phone_number = cleanup_phone_number(conv.caller_number)
    # else:
    #   conv.state.phone_number = ''

    # if not sms_id in conv.sms_templates:
    #     return f"{sms_id} is not a valid template_id."

    # prior to narvar;
    # conv.state.sms_id = "Tracking link"

    conv.state.sms_id = "Narvar tracking link"
    conv.state.sms_content = None
    conv.state.readback_occurred = False

    if conv.state.sent_sms_to_number:
        return {
            "transition": {
                "goto_flow": "SMS flow",
                "goto_step": "Send SMS",
            }
        }
    # if a valid US number, check user wants text sent to their number
    elif is_valid_US_number(conv.state.caller_number_cleanedup):
        return {
            "utterance": utterance(conv, "sms_ask_this_number"),
            "transition": {
                "goto_flow": "SMS flow",
                "goto_step": "Ask this number",
            },
        }
    # if not a valid US number, go straight to collection step
    else:
        return {
            "utterance": utterance(conv, "sms_ask_number"),
            "transition": {
                "goto_flow": "SMS flow",
                "goto_step": "Phone number collected",
            },
        }
