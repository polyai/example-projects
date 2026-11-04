from _gen import *  # <AUTO GENERATED>
import functions.api_client as api_client
import functions.idnv as idnv
import functions.visits as visits
from functions.handoff import handoff
from functions.start_send_sms import (
    ASK_NUMBER,
    CALLING_NUMBER_KEY,
    CALLING_NUMBER_QUESTION,
    no_mobile_line,
)

READBACK_KEY = "sms_number"

MAX_UNCLEAR = 3  # unusable numbers; the third hands off
CALL_AGAIN = (
    "Then call send_link again with whatever they say, even if it's the same as before."
)


def _sms(conv) -> dict:
    sms = conv.state.sms
    return (
        dict(sms)
        if isinstance(sms, dict)
        else {"template": "pay-online", "pending": "", "retries": 0, "sent_to": ""}
    )


def _sent_line(conv, digits: str) -> str:
    calling = idnv.normalize_phone(conv.state.caller_phone)
    where = "over to you" if digits == calling else "to that number"
    return f"I've sent the link {where} now. Is there anything else I can help with?"


def _readback(digits: str) -> str:
    return f"Sure. That's {idnv.spell_phone(digits)}. Shall I send it there?"


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
                "I'm sorry, that text didn't go through. Let me put you through to the team. "
                "One moment, please.",
                "CUSTOMER_CARE",
            )
        conv.write_metric("SMS_SENT", sms["template"])
    sms["sent_to"] = digits
    sms["pending"] = ""
    conv.state.sms = sms
    conv.exit_flow()
    return {"utterance": _sent_line(conv, digits)}


@func_description("Settle the number to text the link to, and send it.")
@func_parameter(
    "use_calling_number",
    "'true' if the caller's latest reply was a yes, or an acknowledgement, to the question about the number they're calling from, or they asked for that number themselves. Otherwise 'false'.",
)
@func_parameter(
    "phone_number",
    "A number the caller gave THIS time, as they said it (words or digits) or keyed. Never add or guess digits. Empty string if none.",
)
@func_parameter(
    "number_confirmed",
    "'true' only if the caller's latest reply agreed to the readback question this tool returned. 'Okay', 'sure' or 'yes' to that question is agreement; an answer to something else, a question back or real hesitation is not. Otherwise 'false'.",
)
def send_link(
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
        if visits.same_turn_as_question(conv, CALLING_NUMBER_KEY):
            return visits.ask_again(conv, CALLING_NUMBER_KEY, CALLING_NUMBER_QUESTION)
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
                    "Sorry, that still isn't working. Let me put you through to the team. One "
                    "moment, please.",
                    "CUSTOMER_CARE",
                )
            return (
                f"NOT A FULL NUMBER (attempt {sms['retries']} of {MAX_UNCLEAR}): don't read it "
                "back. Say: \"Sorry, I didn't catch all of that. Could you give me the full mobile "
                'number, starting with the area code?" ' + CALL_AGAIN
            )
        confirmed = str(number_confirmed).strip().lower() == "true"
        if confirmed and digits == sms["pending"]:
            # A yes to the number this tool read back, repeated with the yes: send it.
            if visits.same_turn_as_question(conv, READBACK_KEY):
                return visits.ask_again(conv, READBACK_KEY, _readback(digits))
            return _send(conv, sms, digits)
        sms["pending"] = digits
        conv.state.sms = sms
        visits.mark_question(conv, READBACK_KEY)
        return (
            f'NOT SENT YET. Say exactly: "{_readback(digits)}" Then wait. A yes or an '
            "acknowledgement → call send_link again with number_confirmed='true'; another number "
            "→ call send_link with it."
        )

    if str(number_confirmed).strip().lower() == "true" and sms["pending"]:
        if visits.same_turn_as_question(conv, READBACK_KEY):
            return visits.ask_again(conv, READBACK_KEY, _readback(sms["pending"]))
        return _send(conv, sms, sms["pending"])

    if idnv.is_valid_phone(calling):
        visits.mark_question(conv, CALLING_NUMBER_KEY)
        return (
            f'Ask: "{CALLING_NUMBER_QUESTION}" If they say no, ask "What number should I send it '
            f'to?" {CALL_AGAIN}{no_mobile_line(conv)}'
        )
    return f'Ask: "{ASK_NUMBER}" {CALL_AGAIN}{no_mobile_line(conv)}'
