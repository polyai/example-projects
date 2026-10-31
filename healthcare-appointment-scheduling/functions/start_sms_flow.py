from _gen import *  # <AUTO GENERATED>

# Templates in config/sms_templates.yaml that topics may offer.
SMS_TEMPLATES = ("clinic_address", "appointment_confirmation")


@func_description(
    "Text the caller. Only call this when a topic's actions tell you to, with that sms_id."
)
@func_parameter("sms_id", "The SMS id the topic gives, e.g. 'clinic_address'.")
def start_sms_flow(conv: Conversation, sms_id: str):
    sms_id = (sms_id or "").strip()
    if sms_id not in SMS_TEMPLATES:
        conv.log.warning("Unknown sms_id", sms_id=sms_id)
        return "There's no text message for that. Tell the caller you can't text that, and carry on."
    conv.write_metric("SMS_ACCEPTED", sms_id)
    sms = {
        "template": sms_id,
        "pending": "",
        "retries": 0,
        "sent_to": "",
        "asked_turn": None,
    }
    conv.state.sms = sms
    conv.goto_flow("sms_flow")
    if conv.state.caller_phone:
        from flows.sms_flow.functions.send_text import ask_calling_number

        return ask_calling_number(conv, sms)
    return "Ask which mobile number you should text."
