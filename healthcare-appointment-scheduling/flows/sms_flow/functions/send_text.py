from _gen import *  # <AUTO GENERATED>
import functions.api_client as api_client
import functions.appointments as appointments
import functions.idnv as idnv
from functions.handoff import handoff

MAX_UNCLEAR = 3  # unusable numbers before the team
CALL_AGAIN = (
    "Then call send_text again with whatever they say, even if it's the same as before."
)
CALLING_NUMBER_QUESTION = "Shall I send it to the number you're calling from?"
FAILED_UTTERANCE = (
    "I'm sorry, that text didn't go through. I'll put you through to the team, who can help. "
    "One moment, please."
)
UNCLEAR_UTTERANCE = (
    "I'm sorry, I'm still not catching the number. I'll put you through to the team, who can "
    "help. One moment, please."
)


def sms_state(conv) -> dict:
    sms = conv.state.sms
    if isinstance(sms, dict):
        return dict(sms)
    return {
        "template": "clinic_address",
        "pending": "",
        "unclear": 0,
        "asked_turn": None,
    }


def ask_calling_number(conv, sms: dict) -> str:
    """The question about texting the number they're calling from (never read out)."""
    sms.update(asked_turn=appointments.history_turn(conv), pending="calling")
    conv.state.sms = sms
    return (
        f'Ask: "{CALLING_NUMBER_QUESTION}" Never say the number. {appointments.CONSENT_HINT} '
        "Then call send_text with use_calling_number 'true'. If they'd rather use another "
        'number, ask "What number should I send it to?"'
    )


def _same_turn(conv, sms: dict) -> bool:
    turn = appointments.history_turn(conv)
    return turn is not None and sms.get("asked_turn") == turn


def _send(conv, sms: dict, digits: str, own_number: bool):
    if api_client.use_mock_api(conv):
        conv.log.info("Mock SMS (not sent outside live)", template=sms["template"])
        conv.write_metric("SMS_SENT_MOCK", sms["template"])
    else:
        try:
            conv.send_sms_template(f"+1{digits}", sms["template"])
        except Exception:
            conv.log.error("SMS failed to send", exc_info=True)
            conv.write_metric("SMS_FAILED")
            return handoff(conv, "SMS_FAILURE", FAILED_UTTERANCE)
        conv.write_metric("SMS_SENT", sms["template"])
    sms.update(pending="", sent=True)
    conv.state.sms = sms
    conv.exit_flow()
    where = "over to you" if own_number else "to that number"
    return {
        "utterance": f"I've sent the address {where} now. {appointments.ANYTHING_ELSE}"
    }


@func_description(
    "Settle the number to text the clinic address to, read it back, and send it once the caller agrees."
)
@func_parameter(
    "use_calling_number",
    "'true' only if the caller's latest reply agreed to the question about sending it to the number they're calling from. 'Okay' or 'sure' to that question is agreement.",
)
@func_parameter(
    "phone_number",
    "The number the caller gave to send it to, as digits. Never add or guess digits.",
)
@func_parameter(
    "number_confirmed",
    "'true' only if the caller's latest reply agreed to the readback question this tool returned for this number. 'Okay', 'sure' or 'sounds good' to that question is agreement; a different number, or real hesitation, is not.",
)
def send_text(
    conv: Conversation,
    flow: Flow,
    use_calling_number: str,
    phone_number: str,
    number_confirmed: str,
):
    sms = sms_state(conv)
    if sms.get("sent"):
        return (
            "ALREADY SENT: the address has been texted. Ask if there's anything else."
        )
    calling = idnv.normalize_phone(conv.state.caller_phone)
    given = str(phone_number or "").strip()

    if not given and str(use_calling_number).strip().lower() == "true":
        if not idnv.is_valid_phone(calling):
            return 'There\'s no number to use from this call. Ask: "What mobile number should I send it to?"'
        if _same_turn(conv, sms) and sms.get("pending") == "calling":
            return {"utterance": CALLING_NUMBER_QUESTION}
        return _send(conv, sms, calling, own_number=True)

    if given:
        digits = idnv.normalize_phone(given)
        if not idnv.is_valid_phone(digits):
            sms["unclear"] = int(sms.get("unclear") or 0) + 1
            conv.state.sms = sms
            if sms["unclear"] >= MAX_UNCLEAR:
                return handoff(conv, "SMS_NUMBER_NOT_CAPTURED", UNCLEAR_UTTERANCE)
            return (
                f'NOT A FULL NUMBER (attempt {sms["unclear"]} of {MAX_UNCLEAR}): say "Sorry, I '
                "didn't catch all of that. Could you say the number again for me?\" Never repeat "
                f"the digits they said. {CALL_AGAIN}"
            )
        confirmed = str(number_confirmed).strip().lower() == "true"
        if confirmed and digits == sms.get("pending"):
            if _same_turn(conv, sms):
                return {
                    "utterance": f"That's {idnv.spell_phone(digits)}. Shall I send it there?"
                }
            return _send(conv, sms, digits, own_number=digits == calling)
        sms.update(pending=digits, asked_turn=appointments.history_turn(conv))
        conv.state.sms = sms
        return (
            f"NOT SENT YET: read the number back digit by digit and ask: \"That's "
            f'{idnv.spell_phone(digits)}. Shall I send it there?" {appointments.CONSENT_HINT} '
            "Then call send_text again with the same number and number_confirmed 'true'. If they "
            "correct it, call send_text with the new number."
        )

    if (
        str(number_confirmed).strip().lower() == "true"
        and len(sms.get("pending") or "") == 10
    ):
        if _same_turn(conv, sms):
            return {
                "utterance": f"That's {idnv.spell_phone(sms['pending'])}. Shall I send it there?"
            }
        return _send(conv, sms, sms["pending"], own_number=sms["pending"] == calling)

    if idnv.is_valid_phone(calling):
        return ask_calling_number(conv, sms)
    return 'Ask: "What mobile number should I send it to?"'
