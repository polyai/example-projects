from _gen import *  # <AUTO GENERATED>


@func_description("[Flow] Handle the user's response to the offer of being sent a text message")
@func_parameter(
    "sms_id",
    "The ID of the text message to send. Always use the one provided to you in the relevant prompt.",
)
def start_sms_flow(conv: Conversation, sms_id: str):
    """This function routes to different steps depending on the following logic:

    1. If we've already send an SMS, we use the same phone number as last time
    2. If the caller number is available, we ask if we can send a text to that number
    3. If the caller number is not available, we collect a number from the user

    """
    conv.write_metric("SMS_ACCEPTED")

    # check that the SMS template id is defined on the SMS page
    if not conv.sms_templates.get(sms_id) and sms_id != "TEST":
        sms_id = sms_id.lower()
    if not conv.sms_templates.get(sms_id) and sms_id != "TEST":
        conv.log.warning(f"SMS template {sms_id} is not found", sms_templates=conv.sms_templates)
        conv.exit_flow()
        if conv.language and conv.language.startswith("en-"):
            return {
                "utterance": "I'm really sorry, but I'm still not getting this to send. Is there anything else I can help you with?"
            }
        return "Tell the user that you're having trouble sending the text message, and ask if there's anything else you can help them with."

    conv.state.sms_id = sms_id

    # check if we've already sent an SMS
    if phone_number := conv.state.sms_phone_number:
        return send_sms(conv, phone_number, repeat_sms=True)

    # check if caller number available
    if conv.caller_number:
        conv.goto_flow("SMS flow")
        if conv.language and conv.language.startswith("en-"):
            return {"utterance": "Am I ok to send this to the number you're calling from?"}
        else:
            return "Ask the user if you're ok to send this text message to the number they're calling from."
    else:
        return {
            "content": "Ask the user for the phone number that you can send this text message to.",
            "transition": {
                "goto_flow": "SMS flow",
                "goto_step": "Collect Alternative Phone Number",
            },
        }


def send_sms(conv: Conversation, phone_number, repeat_sms=False):
    """Send the SMS and handle errors"""

    try:
        e2e_testing_numbers = ["+1 (555) 000-1234", "+15135404072"]
        conv.log.info("Caller number", caller_number=conv.caller_number)
        if str(conv.caller_number) not in e2e_testing_numbers:
            conv.send_sms_template(phone_number, conv.state.sms_id)
        conv.state.sms_phone_number = phone_number
        conv.write_metric("SMS_SENT")
        if conv.language and conv.language.startswith("en-"):
            if repeat_sms:
                return {
                    "utterance": "Ok, that's another text message sent. Can I help you with anything else?"
                }
            return {
                "utterance": "Great, I've just sent that. It might take a minute to arrive. Is there anything else I can help you with?"
            }
        else:
            return "Let the user know you've just sent the text message, and that it might take a minute to arrive. Then, ask if there's anything else you can help them with."
    except Exception:
        conv.log.error("Unable to send SMS")
        conv.exit_flow()
        if conv.language and conv.language.startswith("en-"):
            return {
                "utterance": "I'm really sorry, but I'm still not getting this to send. Is there anything else I can help you with?"
            }
        return "Tell the user that you're having trouble sending the text message, and ask if there's anything else you can help them with."
