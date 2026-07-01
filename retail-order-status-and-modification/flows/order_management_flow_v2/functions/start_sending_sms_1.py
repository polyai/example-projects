import re

from _gen import *  # <AUTO GENERATED>


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
def start_sending_sms_1(conv: Conversation, flow: Flow):
    conv.state.coming_from_WISMO = True

    # if not sms_id in conv.sms_templates:
    #     return f"{sms_id} is not a valid template_id."
    conv.state.sms_id = "Tracking link"
    conv.state.sms_content = None
    conv.state.readback_occurred = False

    if conv.state.sent_sms_to_number:
        return {
            "transition": {
                "goto_flow": "SMS flow",
                "goto_step": "Send SMS",
            }
        }
    else:
        conv.goto_flow("SMS flow")
