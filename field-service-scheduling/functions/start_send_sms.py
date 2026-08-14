from _gen import *  # <AUTO GENERATED>
from functions.try_send_sms import try_send_sms


@func_description(
    'Enter the "Send_SMS_flow" (only call this function if instructed to in "Actions")'
)
@func_parameter("sms_id", "the SMS id")
def start_send_sms(conv: Conversation, sms_id: str):
    # In-hours guard: route to queue instead of sending SMS
    if conv.state.routing_enabled:
        return conv.functions.route_call("BILLING_QUESTION")
    conv.write_metric("SMS_ACCEPTED", None, write_once=False)

    conv.state.sms_template_id = sms_id

    conv.state.readback_occurred = False
    conv.state.save_sms_number_retries = 0

    if conv.state.already_sent_to_number:
        return try_send_sms(conv)
    elif conv.state.phone_number:
        return {
            "transition": {
                "goto_flow": "sms_flow",
                "goto_step": "Should Collect SMS Number",
            }
        }
    else:
        return {
            "transition": {"goto_flow": "sms_flow", "goto_step": "Collect SMS Number"}
        }
