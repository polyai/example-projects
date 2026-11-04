import re

from _gen import *  # <AUTO GENERATED>
from functions import idnv, visits
from functions.utils import variant_attr

CALLING_NUMBER_KEY = "sms_calling_number"
SMS_TEMPLATES = ("balance-due", "update-billing-info", "pay-online", "auto-payment")
CALLING_NUMBER_QUESTION = "Shall I send it to the number you're calling from?"
ASK_NUMBER = "What's the best mobile number to send it to?"


def spoken_url(url: str) -> str:
    """'https://www.example-services.com/portal' -> 'example-services dot com slash portal'."""
    text = re.sub(r"^https?://(www\.)?", "", (url or "").strip()).rstrip("/")
    return text.replace(".", " dot ").replace("/", " slash ")


def no_mobile_line(conv) -> str:
    url = variant_attr(conv, "customer_portal_url")
    if not url:
        return ""
    return (
        " If they don't have a mobile, say instead: \"No problem at all. You can find it at "
        f'{spoken_url(url)}."'
    )


@func_description(
    "Text the caller a link, once they've agreed to a text. Only when a topic's actions tell you to, with that sms_id."
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
            f'Ask: "{CALLING_NUMBER_QUESTION}" Then call send_link with their answer, or with the '
            f"number they give instead.{no_mobile_line(conv)}"
        )
    return f'Ask: "{ASK_NUMBER}" Then call send_link with it.{no_mobile_line(conv)}'
