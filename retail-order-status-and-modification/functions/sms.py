"""Texting a link: which link, the offer, the number, the readback and the send.

Shared by start_send_sms (the offer, and a send to the number the caller is calling from)
and send_link (a number the caller gives). Rules held here:
- when the caller ID is usable, the offer and the number are one question ("Would you like
  me to text the tracking link to the number you're calling from?"), and the tool that made
  the offer records it, so a yes in a later turn sends straight away;
- without caller ID, the offer and the number are two questions;
- a number the caller gives is read back digit by digit before anything is sent;
- nothing goes to the caller-ID number unless the caller agreed to it, and a yes in the same
  turn as the question is refused (orders.same_turn_as_ask).
"""

from _gen import *  # <AUTO GENERATED>
import functions.api_client as api_client
import functions.idnv as idnv
import functions.orders as orders
import functions.store_info as store_info
from functions.handoff import handoff

SMS_KEY = "sms"  # the readback key in orders.asked / same_turn_as_ask
MAX_UNCLEAR = 3  # numbers that aren't a full number; the last one transfers

LINK_NAMES = {
    "tracking_link": "the tracking link",
    "website": "the link to our website",
    "returns_portal": "the returns link",
    "store_locator": "the store locator link",
    "promotions": "the link to our offers",
}
NO_TRACKING_LINE = "There's no tracking link yet, as it hasn't shipped. We'll email you one as soon as it does."
FAILED_LINE = (
    "I'm sorry, that text didn't go through. I'll put you through to the team now. One "
    "moment, please."
)
NUMBER_ASK = "What's the best mobile number to send it to?"
PARTIAL_LINE = "Sorry, I only caught part of that. What's the full mobile number, starting with the area code?"
NOT_CAPTURED_LINE = (
    "I'm sorry, I'm not able to take that number down. I'll put you through to the team now. "
    "One moment, please."
)


@func_description("[UTIL] Text-a-link helpers, not callable directly")
def sms(conv: Conversation):
    return "SMS helpers module."


def calling_number(conv) -> str:
    """The caller ID as ten digits when it's usable for a text, else ''."""
    digits = idnv.normalize_phone(conv.state.caller_phone or "")
    return digits if idnv.is_valid_phone(digits) else ""


def link_name(sms_id: str) -> str:
    return LINK_NAMES.get(sms_id, "the link")


def _state(conv) -> dict:
    current = conv.state.sms
    if isinstance(current, dict):
        return dict(current)
    return {"id": "", "order_number": "", "pending": "", "retries": 0, "calling": False}


def _save(conv, s: dict) -> None:
    conv.state.sms = s


def link_body(conv, sms_id: str, order_number: str = "") -> str:
    """The text for a link, or '' when there's nothing to send."""
    if sms_id == "tracking_link":
        order = None
        if idnv.is_verified(conv):
            listed = orders.caller_orders(conv)
            order = next((o for o in listed if o["order_number"] == order_number), None)
            order = order or orders.selected_order(conv, listed)
        url = orders.tracking_url(order) if order else ""
        return f"Track your order here: {url}" if url else ""
    if sms_id in store_info.LINKS:
        return store_info.sms_body(conv, sms_id)
    return ""


def offer(
    conv,
    sms_id: str,
    order_number: str = "",
    for_items: str = "",
    extra: str = "",
    question: str = "",
) -> str:
    """The offer question, recorded as asked. With a usable caller ID it names the number the
    caller is calling from, so a yes sends."""
    name = link_name(sms_id) + (f" for the {for_items}" if for_items else "")
    usable = bool(calling_number(conv))
    if question:
        pass
    elif usable:
        question = f"Would you like me to text {name} to the number you're calling from{extra}?"
    else:
        question = f"Would you like me to text you {name}{extra}?"
    s = _state(conv)
    s.update(
        id=sms_id,
        order_number=order_number or s.get("order_number", ""),
        calling=usable,
    )
    s["offered"] = sms_id
    _save(conv, s)
    orders.asked(conv, SMS_KEY, question)
    return question


def offered(conv, sms_id: str) -> dict | None:
    s = _state(conv)
    return s if s.get("offered") == sms_id else None


def ask_calling_number(conv, sms_id: str) -> str:
    """The caller asked for a text themselves: ask about the calling number first."""
    question = "Sure. Shall I send it to the number you're calling from?"
    s = _state(conv)
    s.update(id=sms_id, calling=True, offered=sms_id)
    _save(conv, s)
    orders.asked(conv, SMS_KEY, question)
    return question


def begin(conv, sms_id: str, order_number: str = "") -> None:
    """Start collecting a number for sms_id (keeps the order the offer was about)."""
    s = _state(conv)
    s.update(id=sms_id, pending="", retries=0)
    if order_number:
        s["order_number"] = order_number
    _save(conv, s)


def number_question(digits: str) -> str:
    """The readback before a text goes to a number the caller gave."""
    return f"That's {idnv.spell_phone(digits)}. Shall I send it there?"


def take_number(conv, said: str, tool: str) -> str | dict:
    """A number the caller gave: count it if it isn't a full number, else read it back."""
    s = _state(conv)
    digits = idnv.normalize_phone(said)
    if not idnv.is_valid_phone(digits):
        s["retries"] = int(s.get("retries") or 0) + 1
        _save(conv, s)
        if s["retries"] >= MAX_UNCLEAR:
            return handoff(
                conv,
                "SMS_PHONE_NUMBER_COLLECTION_FAIL",
                NOT_CAPTURED_LINE,
                "CUSTOMER_SERVICE",
            )
        return (
            f'NOT A FULL NUMBER (attempt {s["retries"]} of {MAX_UNCLEAR}): say "{PARTIAL_LINE}" '
            f"Never repeat the digits they said. {orders.call_again(tool)}"
        )
    s.update(pending=digits, offered="")
    _save(conv, s)
    question = number_question(digits)
    orders.asked(conv, SMS_KEY, question)
    return (
        f'NOT SENT YET. Read the number back and ask, in these words: "{question}" Say the '
        f"digits exactly as written. Wait for the answer. {orders.YES_LINE}: then call send_link "
        "with the same number and number_confirmed='true'. If they correct the number, call "
        "send_link with the new number and number_confirmed='false'."
    )


def pending_number(conv) -> str:
    return _state(conv).get("pending", "")


def send(conv, digits: str, to_calling: bool) -> dict:
    """Send the current link to digits and return the done line as the utterance."""
    s = _state(conv)
    sms_id = s.get("id") or "website"
    body = link_body(conv, sms_id, s.get("order_number", ""))
    if not body:
        return {"utterance": NO_TRACKING_LINE + f" {orders.ANYTHING_ELSE}"}
    conv.state.sms_body = body
    if api_client.use_mock_api(conv):
        conv.log.info("Mock SMS (not sent outside live)", template="store_link")
        conv.write_metric("SMS_SENT_MOCK", sms_id)
    else:
        try:
            conv.send_sms_template(f"+1{digits}", "store_link")
        except Exception:
            conv.log.error("SMS failed to send", exc_info=True)
            conv.write_metric("SMS_FAILED")
            return handoff(conv, "CANNOT_SEND_SMS", FAILED_LINE, "CUSTOMER_SERVICE")
        conv.write_metric("SMS_SENT", sms_id)
    s.update(pending="", offered="", sent_to=digits)
    _save(conv, s)
    orders.forget_readback(conv, SMS_KEY)
    where = "over to you" if to_calling else "to that number"
    return {
        "utterance": f"I've sent {link_name(sms_id)} {where} now. {orders.ANYTHING_ELSE}",
    }
