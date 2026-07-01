import re

from _gen import *  # <AUTO GENERATED>

from .utterances import utterance


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


@func_description(
    "The user has said yes to a text message. Call this function to collect the number and send the message"
)
@func_parameter("sms_id", "the SMS template to use")
def send_sms_message(conv: Conversation, sms_id: str):
    # Use French SMS template for fr-CA callers if available
    if conv.state.language == "fr-CA":
        fr_id = f"{sms_id}-fr"
        if fr_id in conv.sms_templates:
            sms_id = fr_id

    if sms_id not in conv.sms_templates:
        return f"{sms_id} is not a valid template_id. "

    conv.write_metric("SMS_OFFERED", write_once=True)
    conv.write_metric("SMS_ACCEPTED")
    conv.write_metric("SMS_ID", sms_id)
    conv.state.sms_id = sms_id
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
