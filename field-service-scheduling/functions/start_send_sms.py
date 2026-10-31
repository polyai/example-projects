from _gen import *  # <AUTO GENERATED>
from functions import idnv, visits

CALLING_NUMBER_KEY = "sms_calling_number"
SMS_TEMPLATES = ("balance-due", "update-billing-info", "pay-online", "auto-payment")


@func_description(
    "Text the caller a link. Only call this when a topic's actions tell you to, with that sms_id."
)
@func_parameter("sms_id", "The SMS id the topic gives, e.g. 'pay-online'.")
def start_send_sms(conv: Conversation, sms_id: str):
    sms_id = (sms_id or "").strip()
    if sms_id not in SMS_TEMPLATES:
        conv.log.warning("Unknown sms_id", sms_id=sms_id)
        sms_id = "pay-online"
    conv.write_metric("SMS_ACCEPTED")
    conv.state.sms = {"template": sms_id, "pending": "", "retries": 0, "sent_to": ""}
    conv.goto_flow("sms_flow")
    if idnv.is_valid_phone(idnv.normalize_phone(conv.state.caller_phone)):
        visits.mark_question(conv, CALLING_NUMBER_KEY)
        return (
            visits.yes_no_question(
                "text the link to the number they're calling from", "Ask"
            )
            + " Then call send_link with their answer, or with the number they give instead."
        )
    return "Ask which mobile number you should text the link to. Then call send_link with it."
