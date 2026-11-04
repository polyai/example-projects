from _gen import *  # <AUTO GENERATED>
from functions import billing, idnv

# Questions held in code (design 2.4). None of them says a number.
CALLING_NUMBER_QUESTION = "Shall I send it to the number you're calling from?"
ACCOUNT_NUMBER_QUESTION = "Shall I send it to the number on your account?"
SAME_NUMBER_QUESTION = "Shall I send it to the same number as before?"
WHICH_NUMBER_QUESTION = "What's the best mobile number to send it to?"
ALREADY_SENT = (
    "I've already sent that one, so it should be with you shortly. Is there anything else I can "
    "help with?"
)
NO_PAYMENT_TO_CONFIRM = (
    "I can only text a confirmation for a payment made on this call."
)

# Templates that carry account details: strict ID&V first, and only to the number the caller is
# calling from or the number on the account, so a payment is never shown to someone else.
ACCOUNT_TEMPLATES = ("payment_confirmation",)


def fresh(sms_id: str) -> dict:
    return {
        "template": sms_id,
        "pending": "",  # the number a yes would send to
        "offered": "",  # what the last question asked about: caller_id | account | previous | number | ask
        "retries": 0,
        "sent_to": "",
        "asked_turn": None,
    }


def calling_number(conv) -> str:
    digits = idnv.normalize_phone(conv.state.caller_phone)
    return digits if idnv.is_valid_phone(digits) else ""


def account_number(conv) -> str:
    """The verified account's phone number, never said aloud."""
    digits = idnv.state(conv).get("phone") or ""
    return (
        digits
        if idnv.is_verified(conv, idnv.STRICT) and idnv.is_valid_phone(digits)
        else ""
    )


def ask(conv, sms: dict, offered: str, question: str, pending: str = "") -> str:
    sms.update(offered=offered, pending=pending, asked_turn=billing.history_turn(conv))
    conv.state.sms = sms
    return (
        f'Ask, in these words: "{question}" Never say the number. Then call send_text with their '
        "answer: a yes, or an acknowledgement, to the question is agreement."
    )


def first_question(conv, sms: dict) -> str:
    """The first number question for this text."""
    calling = calling_number(conv)
    if sms["template"] in ACCOUNT_TEMPLATES:
        if calling:
            return ask(conv, sms, "caller_id", CALLING_NUMBER_QUESTION, calling)
        return ask(conv, sms, "account", ACCOUNT_NUMBER_QUESTION, account_number(conv))
    previous = idnv.normalize_phone(conv.state.sms_phone_number)
    if idnv.is_valid_phone(previous):
        return ask(conv, sms, "previous", SAME_NUMBER_QUESTION, previous)
    if calling:
        return ask(conv, sms, "caller_id", CALLING_NUMBER_QUESTION, calling)
    sms.update(offered="ask", pending="", asked_turn=billing.history_turn(conv))
    conv.state.sms = sms
    return (
        "If the caller has already said a number to text, call send_text with it now, before you "
        "reply, with number_confirmed 'false': it reads the number back. Otherwise ask: "
        f'"{WHICH_NUMBER_QUESTION}" Then pass whatever they say to send_text, as they said it, '
        "even if it sounds incomplete. Read back only what send_text returns."
    )


@func_description(
    "Text the caller a message. Only call this when a topic or tool tells you to, with that sms_id, or when they ask for a text confirming a payment made on this call (sms_id 'payment_confirmation')."
)
@func_parameter(
    "sms_id", "The SMS id the topic or tool gives, e.g. 'change_personal_address_app'."
)
def start_send_sms(conv: Conversation, sms_id: str):
    sms_id = (sms_id or "").strip()
    templates = conv.sms_templates if isinstance(conv.sms_templates, dict) else {}
    if templates and sms_id not in templates and sms_id.lower() in templates:
        sms_id = sms_id.lower()
    if templates and sms_id not in templates:
        conv.log.warning("Unknown sms_id", sms_id=sms_id)
        return (
            "That text message isn't available. Say you can't send that one, give the one or two "
            "steps out loud instead, and ask if there's anything else."
        )

    if sms_id in ACCOUNT_TEMPLATES:
        gate = billing.gate(conv, "sms_flow")
        if gate:
            conv.state.sms = fresh(sms_id)
            return gate
        if not conv.state.last_confirmation_number:
            return f'Say: "{NO_PAYMENT_TO_CONFIRM}" Then ask if there\'s anything else.'

    sent = conv.state.sms_sent if isinstance(conv.state.sms_sent, list) else []
    if sms_id in sent:
        return {"utterance": ALREADY_SENT}

    conv.write_metric("SMS_ACCEPTED")
    sms = fresh(sms_id)
    conv.goto_flow("sms_flow")
    return first_question(conv, sms)
