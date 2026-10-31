from _gen import *  # <AUTO GENERATED>
from functions import billing, idnv

SAME_NUMBER_QUESTION = (
    "Shall I send it to the same number as your last text, yes or no?"
)

# Templates that carry account details: strict ID&V first, checked here in code.
ACCOUNT_TEMPLATES = ("payment_confirmation",)


def _fresh(sms_id: str) -> dict:
    return {
        "template": sms_id,
        "pending": "",
        "retries": 0,
        "sent_to": "",
        "asked_turn": None,
    }


@func_description(
    "Text the caller a message. Only call this when a topic or tool tells you to, with that sms_id."
)
@func_parameter(
    "sms_id", "The SMS id the topic or tool gives, e.g. 'forgot_customer_number_app'."
)
def start_send_sms(conv: Conversation, sms_id: str):
    sms_id = (sms_id or "").strip()
    templates = conv.sms_templates if isinstance(conv.sms_templates, dict) else {}
    if templates and sms_id not in templates and sms_id.lower() in templates:
        sms_id = sms_id.lower()
    if templates and sms_id not in templates:
        conv.log.warning("Unknown sms_id", sms_id=sms_id)
        return "That text message isn't available. Say you can't send it, and ask if there's anything else."

    if sms_id in ACCOUNT_TEMPLATES:
        gate = billing.gate(conv, "sms_flow")
        if gate:
            conv.state.sms = _fresh(sms_id)
            return gate
        if not conv.state.last_confirmation_number:
            return "There's no payment or transfer from this call to confirm. Say so and ask if there's anything else."

    sent = conv.state.sms_sent if isinstance(conv.state.sms_sent, list) else []
    if sms_id in sent:
        return (
            "That text has already been sent on this call; don't send it again. Tell the caller "
            "it's on its way and may take a minute, then ask if there's anything else."
        )

    conv.write_metric("SMS_ACCEPTED")
    conv.state.sms = _fresh(sms_id)
    conv.goto_flow("sms_flow")
    if conv.state.sms_phone_number:
        conv.state.sms = {**_fresh(sms_id), "asked_turn": billing.history_turn(conv)}
        return (
            f'Ask the caller, in these words: "{SAME_NUMBER_QUESTION}" Then wait for their '
            "answer. On a clear yes, call send_text with number_confirmed 'true'; if they give "
            "another number, pass it to send_text as they said it. Read back only what send_text "
            "returns."
        )
    if idnv.is_valid_phone(idnv.normalize_phone(conv.state.caller_phone)):
        conv.state.sms = {**_fresh(sms_id), "asked_turn": billing.history_turn(conv)}
        return billing.TEXT_CALLING_NUMBER_OFFER
    return (
        "Ask which mobile number you should text, then pass whatever they say to send_text, as "
        "they said it, even if it sounds incomplete. Read back only what send_text returns."
    )
