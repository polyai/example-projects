from _gen import *  # <AUTO GENERATED>
import functions.api_client as api_client
import functions.appointments as appointments
import functions.idnv as idnv
from functions.handoff import handoff

MAX_UNCLEAR = 2
TRIES = MAX_UNCLEAR + 1  # the third unclear number transfers
CALL_AGAIN = (
    "Then call send_text again with whatever they say, even if it's the same as before."
)
# What each text is, as the confirmation question names it.
TEXT_NAMES = {
    "clinic_address": "the clinic address",
    "appointment_confirmation": "the confirmation",
}


def _sms(conv) -> dict:
    sms = conv.state.sms
    if isinstance(sms, dict):
        return dict(sms)
    return {"template": "clinic_address", "pending": "", "retries": 0, "sent_to": ""}


def text_words(sms: dict, to: str) -> str:
    """The texting confirmation the caller hears: what the text is and where it goes."""
    what = TEXT_NAMES.get(sms.get("template"), "it")
    return f"Shall I text {what} to {to}, yes or no?"


def ask_calling_number(conv, sms: dict) -> str:
    """The yes-or-no question about texting the number they're calling from."""
    sms["asked_turn"] = appointments.history_turn(conv)
    conv.state.sms = sms
    return appointments.ask_yes_no(text_words(sms, "the number you're calling from"))


def _asked_this_turn(conv, sms: dict) -> bool:
    turn = appointments.history_turn(conv)
    return turn is not None and sms.get("asked_turn") == turn


def _send(conv, sms: dict, digits: str):
    if api_client.use_mock_api(conv):
        conv.log.info("Mock SMS (not sent outside live)", template=sms["template"])
        conv.write_metric("SMS_SENT_MOCK", sms["template"])
    else:
        try:
            conv.send_sms_template(f"+1{digits}", sms["template"])
        except Exception:
            conv.log.error("SMS failed to send", exc_info=True)
            conv.write_metric("SMS_FAILED")
            return handoff(
                conv,
                "SMS_FAILURE",
                "I'm sorry, that text didn't go through. Let me put you through to a colleague, "
                "one moment please.",
            )
        conv.write_metric("SMS_SENT", sms["template"])
    sms.update(sent_to=digits, pending="")
    conv.state.sms = sms
    conv.exit_flow()
    return (
        "Sent. Tell the caller the text is on its way (don't read the number again), then ask "
        "if there's anything else."
    )


@func_description("Settle the number to text, and send the message.")
@func_parameter(
    "use_calling_number",
    "'true' only if the caller's latest reply was a clear yes to the yes-or-no question about texting the number they're calling from, or they asked for that number themselves. 'Okay', 'mm-hm', 'sure, whatever', silence or a question is not a yes: ask the yes-or-no question again. Otherwise 'false'.",
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
        if _asked_this_turn(conv, sms):
            return appointments.NOT_DONE_YET
        return _send(conv, sms, calling)

    if str(phone_number or "").strip():
        digits = idnv.normalize_phone(phone_number)
        if not idnv.is_valid_phone(digits):
            sms["retries"] += 1
            conv.state.sms = sms
            if sms["retries"] > MAX_UNCLEAR:
                return handoff(
                    conv,
                    "SMS_FAILURE",
                    "Sorry, that still isn't working. Let me put you through to a colleague, one "
                    "moment please.",
                )
            return (
                f"NOT A FULL NUMBER (attempt {sms['retries']} of {TRIES}): ask for the ten-digit "
                f"mobile number, starting with the area code. {CALL_AGAIN}"
            )
        confirmed = str(number_confirmed).strip().lower() == "true"
        if confirmed and digits == (sms["pending"] or digits):
            # A yes to this same number (or to a readback the agent gave itself): send it.
            if _asked_this_turn(conv, sms):
                return appointments.NOT_DONE_YET
            return _send(conv, sms, digits)
        sms["pending"] = digits
        sms["asked_turn"] = appointments.history_turn(conv)
        conv.state.sms = sms
        spelled = idnv.spell_phone(digits)
        return (
            f"{appointments.ask_yes_no(text_words(sms, spelled), 'Read the number back exactly as written')} "
            "On a clear yes, call send_text with number_confirmed='true'; if they correct it, "
            "call send_text with the corrected number."
        )

    if str(number_confirmed).strip().lower() == "true" and sms["pending"]:
        if _asked_this_turn(conv, sms):
            return appointments.NOT_DONE_YET
        return _send(conv, sms, sms["pending"])

    if idnv.is_valid_phone(calling):
        return (
            ask_calling_number(conv, sms)
            + " If they'd rather use another number, ask which."
        )
    return "Ask which mobile number to text."
