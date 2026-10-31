from _gen import *  # <AUTO GENERATED>
import functions.api_client as api_client
import functions.bookings as bookings
import functions.idnv as idnv
from functions.handoff import handoff

MAX_UNCLEAR = 3  # unclear numbers before the caller is put through
CALL_AGAIN = (
    "Then call send_text again with whatever they say, even if it's the same as before."
)
ASKED_KEY = "sms"


CALLING_QUESTION = "Shall I text the link to the number you're calling from"


def number_question(digits: str) -> str:
    return f"Shall I text the link to {idnv.spell_phone(digits)}"


def ask_number(conv, digits: str) -> str:
    """Read a number back as a yes-or-no question about texting it."""
    bookings.mark_asked(conv, ASKED_KEY)
    return (
        bookings.ask_yes_no(number_question(digits))
        + " On a clear yes, call send_text again with that number and number_confirmed='true'; "
        "if they correct it, call send_text with the corrected number."
    )


def ask_calling_number(conv) -> str:
    """Ask whether to text the number they're calling from, as a yes-or-no question."""
    bookings.mark_asked(conv, ASKED_KEY)
    return (
        bookings.ask_yes_no(CALLING_QUESTION)
        + " On a clear yes, call send_text with use_calling_number='true'; if they give "
        "another number, call send_text with it."
    )


def _sms(conv) -> dict:
    sms = conv.state.sms
    return (
        dict(sms)
        if isinstance(sms, dict)
        else {"template": "menu", "pending": "", "retries": 0, "sent_to": ""}
    )


def _send(conv, sms: dict, digits: str):
    number = f"+1{digits}"
    if api_client.use_mock_api(conv):
        conv.log.info("Mock SMS (not sent outside live)", template=sms["template"])
        conv.write_metric("SMS_SENT_MOCK", sms["template"])
    else:
        try:
            conv.send_sms_template(number, sms["template"])
        except Exception:
            conv.log.error("SMS failed to send", exc_info=True)
            conv.write_metric("SMS_FAILED")
            return handoff(
                conv,
                "CANNOT_SEND_SMS",
                "I'm sorry, that text didn't go through. Let me put you through to the team, "
                "one moment please.",
            )
        conv.write_metric("SMS_SENT", sms["template"])
    sms["sent_to"] = digits
    sms["pending"] = ""
    conv.state.sms = sms
    back_to = conv.state.sms_return_flow
    conv.state.sms_return_flow = ""
    if back_to:
        # Texted in the middle of a task (e.g. the menu while booking): pick the task back up.
        conv.goto_flow(back_to)
        return (
            "Sent. Tell the caller the text is on its way (don't read the number again), then "
            "carry on where you left off without asking again for anything they've told you."
        )
    conv.exit_flow()
    return (
        "Sent. Tell the caller the text is on its way (don't read the number again), then ask if "
        "there's anything else."
    )


@func_description(
    "Settle the number to text the link to, and send it. Call it whenever the caller gives a number, agrees to the number they're calling from, or answers the readback."
)
@func_parameter(
    "use_calling_number",
    "'true' only if the caller's latest reply was a clear yes to texting the number they're calling from, or they asked for it. 'Okay' or anything unclear is not a yes. Otherwise 'false'.",
)
@func_parameter(
    "phone_number",
    "A number the caller gave THIS time, as they said it (words or digits). Never add or guess digits. Empty string if none.",
)
@func_parameter(
    "number_confirmed",
    "'true' only if the caller's latest reply was a clear yes to the yes-or-no question this tool's readback asked. 'Okay', 'mm-hm', 'sure, whatever', silence or a question is not a yes: ask the yes-or-no question again. Otherwise 'false'.",
)
def send_text(
    conv: Conversation,
    flow: Flow,
    use_calling_number: str,
    phone_number: str,
    number_confirmed: str,
):
    sms = _sms(conv)
    calling = idnv.normalize_phone(conv.state.caller_phone)

    if str(use_calling_number).strip().lower() == "true" and idnv.is_valid_phone(
        calling
    ):
        if bookings.asked_this_turn(conv, ASKED_KEY):
            return bookings.not_done_yet(CALLING_QUESTION)
        return _send(conv, sms, calling)

    if str(phone_number or "").strip():
        digits = idnv.normalize_phone(phone_number)
        if not idnv.is_valid_phone(digits):
            sms["retries"] += 1
            conv.state.sms = sms
            if sms["retries"] >= MAX_UNCLEAR:
                return handoff(
                    conv,
                    "SMS_PHONE_NUMBER_COLLECTION_FAIL",
                    "Sorry, that still isn't working. Let me put you through to the team, one "
                    "moment please.",
                )
            return (
                f"NOT A FULL NUMBER (attempt {sms['retries']} of {MAX_UNCLEAR}): ask for the "
                f"ten-digit mobile number, starting with the area code. {CALL_AGAIN}"
            )
        confirmed = str(number_confirmed).strip().lower() == "true"
        if confirmed and digits == (sms["pending"] or digits):
            # A yes to this same number (or to a readback the agent gave itself): send it,
            # unless the caller hasn't answered the readback yet.
            if sms["pending"] and bookings.asked_this_turn(conv, ASKED_KEY):
                return bookings.not_done_yet(number_question(sms["pending"]))
            return _send(conv, sms, digits)
        sms["pending"] = digits
        conv.state.sms = sms
        return f"NOT SENT YET. {ask_number(conv, digits)}"

    if str(number_confirmed).strip().lower() == "true" and sms["pending"]:
        if bookings.asked_this_turn(conv, ASKED_KEY):
            return bookings.not_done_yet(number_question(sms["pending"]))
        return _send(conv, sms, sms["pending"])

    if idnv.is_valid_phone(calling):
        return f"NOT SENT YET. {ask_calling_number(conv)}"
    return f"NOT SENT YET. Ask which mobile number to text the link to. {CALL_AGAIN}"
