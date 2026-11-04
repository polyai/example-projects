from _gen import *  # <AUTO GENERATED>
import functions.api_client as api_client
import functions.bookings as bookings
import functions.idnv as idnv
import functions.texts as texts
from functions.handoff import handoff

MAX_UNCLEAR = 3  # unclear numbers before the caller is put through
CALL_AGAIN = (
    "Then call send_text again with whatever they say, even if it's the same as before."
)


def _sms(conv) -> dict:
    sms = conv.state.sms
    return (
        dict(sms)
        if isinstance(sms, dict)
        else {"template": "menu", "pending": "", "retries": 0, "sent_to": ""}
    )


def _send(conv, sms: dict, digits: str, calling: bool):
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
                "I'm sorry, that text didn't go through. Let me put you through to the team. "
                "One moment, please.",
            )
        conv.write_metric("SMS_SENT", sms["template"])
    sms["sent_to"] = digits
    sms["pending"] = ""
    conv.state.sms = sms
    sent = texts.SENT_CALLING if calling else texts.SENT_OTHER
    back_to = conv.state.sms_return_flow
    conv.state.sms_return_flow = ""
    if back_to:
        # Texted in the middle of a task (the menu while booking): pick the task back up.
        conv.goto_flow(back_to)
        return (
            f'SENT. Say "{sent}" (never read the number again), then carry on where you left '
            "off, without asking again for anything they've told you."
        )
    conv.exit_flow()
    line = f"{sent} {texts.ANYTHING_ELSE}"
    bookings.said_line(conv, line)
    return {"utterance": line}


@func_description(
    "Settle the number to text the link to, and send it. Call it whenever the caller gives a number, or answers the question this tool or start_send_text asked."
)
@func_parameter(
    "use_calling_number",
    "'true' only if the caller's latest reply agreed to the question whether to send it to the number they're calling from ('okay' or 'sure' to it is agreement). Otherwise 'false'.",
)
@func_parameter(
    "phone_number",
    "A number the caller gave THIS time, as they said it (words or digits). Never add or guess digits. Empty string if none.",
)
@func_parameter(
    "number_confirmed",
    "'true' only if the caller's latest reply agreed to the readback question this tool returned. 'Okay', 'sure' or 'sounds good' to that question is agreement; an answer to something else, or real hesitation, is not. Otherwise 'false'.",
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

    if bookings.is_true(use_calling_number) and idnv.is_valid_phone(calling):
        if bookings.asked_this_turn(conv, texts.ASKED_KEY):
            return bookings.not_done_yet(texts.CALLING_QUESTION)
        return _send(conv, sms, calling, calling=True)

    if str(phone_number or "").strip():
        digits = idnv.normalize_phone(phone_number)
        if not idnv.is_valid_phone(digits):
            sms["retries"] += 1
            conv.state.sms = sms
            if sms["retries"] >= MAX_UNCLEAR:
                return handoff(
                    conv,
                    "SMS_PHONE_NUMBER_COLLECTION_FAIL",
                    "I'm sorry, I'm having trouble catching the number. Let me put you through to "
                    "the team. One moment, please.",
                )
            return (
                f'NOT A FULL NUMBER (attempt {sms["retries"]} of {MAX_UNCLEAR}): say "Sorry, I '
                "didn't catch all of that. Could you say the full number again for me?\" "
                f"{CALL_AGAIN}"
            )
        if bookings.is_true(number_confirmed) and digits == sms["pending"]:
            # A yes with the number repeated: send it, unless the caller hasn't answered yet.
            if bookings.asked_this_turn(conv, texts.ASKED_KEY):
                return bookings.not_done_yet(texts.number_sentence(sms["pending"]))
            return _send(conv, sms, digits, calling=False)
        sms["pending"] = digits
        conv.state.sms = sms
        return f"NOT SENT YET. {texts.ask_number(conv, digits)}"

    if bookings.is_true(number_confirmed) and sms["pending"]:
        if bookings.asked_this_turn(conv, texts.ASKED_KEY):
            return bookings.not_done_yet(texts.number_sentence(sms["pending"]))
        return _send(conv, sms, sms["pending"], calling=False)

    if idnv.is_valid_phone(calling):
        return f"NOT SENT YET. {texts.ask_calling_number(conv)}"
    return f"NOT SENT YET. {texts.ask_mobile()} {CALL_AGAIN}"
