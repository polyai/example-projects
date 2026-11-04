from _gen import *  # <AUTO GENERATED>
import functions.idnv as idnv

# Texts a topic may offer. appointment_confirmation carries no day, time or doctor, so it
# isn't offered until it does.
SMS_TEMPLATES = ("clinic_address",)
CALLING_NUMBER_QUESTION = "Shall I send it to the number you're calling from?"


@func_description(
    "Text the caller the clinic address. Only call this when a topic's actions tell you to, with that sms_id."
)
@func_parameter("sms_id", "The SMS id the topic gives, e.g. 'clinic_address'.")
def start_sms_flow(conv: Conversation, sms_id: str):
    sms_id = (sms_id or "").strip()
    if sms_id not in SMS_TEMPLATES:
        conv.log.warning("Unknown sms_id", sms_id=sms_id)
        return (
            "There's no text for that. Say you're afraid you can't text that, offer to read it "
            "out instead, and carry on."
        )
    conv.write_metric("SMS_ACCEPTED", sms_id)
    calling = idnv.normalize_phone(conv.state.caller_phone)
    sms = {"template": sms_id, "pending": "", "unclear": 0, "asked_turn": None}
    conv.goto_flow("sms_flow")
    if idnv.is_valid_phone(calling):
        try:
            sms["asked_turn"] = len(conv.history)
        except Exception:
            sms["asked_turn"] = None
        sms["pending"] = "calling"
        conv.state.sms = sms
        return (
            f'Ask: "{CALLING_NUMBER_QUESTION}" Never say the number. A yes, or an '
            'acknowledgement ("okay", "sure"), means call send_text with use_calling_number '
            "'true'. If they'd rather use another, ask \"What number should I send it to?\""
        )
    conv.state.sms = sms
    return (
        "If they've already given a number, call send_text with it now; otherwise ask: \"What "
        'mobile number should I send it to?" Call send_text with the number before reading '
        "anything back."
    )
