from _gen import *  # <AUTO GENERATED>
from functions.send_sms import send_sms
from functions.util_functions import is_valid_potential_mobile_number


@func_description("Enter the SMS flow with the relevant template_id")
@func_parameter("template_id", "the SMS template to use")
def start_sms_flow(conv: Conversation, template_id: str):
    if template_id not in conv.sms_templates:
        return f"{template_id} is not a valid template_id. "
    conv.write_metric("SMS_ACCEPTED")
    conv.write_metric("SMS_ID", template_id)
    conv.state.sms_template_id = template_id
    conv.state.readback_occurred = False
    if conv.current_flow in ["make_booking", "confirm_cancel_modify_booking"]:
        conv.state.origin_flow = conv.current_flow
        conv.state.origin_step = conv.current_step

    if conv.state.already_sent_to_number:
        return send_sms(conv, conv.state.sms_phone_number)
    elif is_valid_potential_mobile_number(conv, conv.caller_number):
        return {
            "transition": {
                "goto_flow": "sms_flow",
                "goto_step": "Ask this number",
            }
        }
    else:
        return {
            "transition": {
                "goto_flow": "sms_flow",
                "goto_step": "Collect phone number",
            }
        }
