from _gen import *  # <AUTO GENERATED>
import functions.api_client as api_client
import functions.billing as billing
import functions.idnv as idnv
from functions.handoff import transfer

MAX_UNCLEAR = 3  # numbers that aren't a full phone number before the transfer
TOOL = "send_text"
# Every return that needs another answer ends with this: Dialog-RSN-1 won't repeat a check on
# its own, and reads a number back itself unless told the tool does it.
CALL_AGAIN = (
    f"Then call {TOOL} again with whatever number they say, as they said it, even if it's the same "
    "or sounds incomplete. Read back only what this tool returns."
)


def number_question(digits: str) -> str:
    """The readback and the yes-or-no question as one short sentence."""
    return f"Shall I send the text to {idnv.spell_phone(digits)}, yes or no?"


def _sms(conv) -> dict:
    sms = conv.state.sms
    return (
        dict(sms)
        if isinstance(sms, dict)
        else {
            "template": "",
            "pending": "",
            "retries": 0,
            "sent_to": "",
            "asked_turn": None,
        }
    )


def _same_turn_as_question(conv, sms: dict) -> bool:
    """The number's yes-or-no question was asked in this same turn (history length unchanged),
    so the caller can't have answered it yet. The length is a marker only."""
    turn = billing.history_turn(conv)
    return (
        turn is not None
        and sms.get("asked_turn") is not None
        and turn == sms["asked_turn"]
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
            conv.exit_flow()
            return (
                "The text didn't go through. Apologise, say you couldn't send it, and ask if "
                "there's anything else."
            )
        conv.write_metric("SMS_SENT", sms["template"])
    sms["sent_to"] = digits
    sms["pending"] = ""
    conv.state.sms = sms
    conv.state.sms_phone_number = digits
    sent = conv.state.sms_sent if isinstance(conv.state.sms_sent, list) else []
    conv.state.sms_sent = sent + [sms["template"]]
    conv.exit_flow()
    return (
        "Sent. Tell the caller the text is on its way and may take a minute (don't read the "
        "number again), then ask if there's anything else."
    )


@func_description(
    "Settle the number to text and send the message. Pass whatever number the caller gives, as they said it, even if it sounds incomplete: this tool checks it and returns the readback. Never read a number back or say it's wrong before it returns."
)
@func_parameter(
    "use_calling_number",
    "'true' only if the caller's latest reply was a clear yes to texting the number they're calling from. 'Okay', 'mm-hm', silence or a question is not a yes. Otherwise 'false'.",
)
@func_parameter(
    "phone_number",
    "A number the caller gave THIS time, as they said it (words or digits), even if it sounds incomplete. Apply a partial correction to the number you read back and pass the full number. Never add or guess digits. Empty if none.",
)
@func_parameter(
    "number_confirmed",
    "'true' only if the caller's latest reply was a clear yes to the yes-or-no question this tool's readback (or offer) asked. 'Okay', 'mm-hm', 'sure, whatever', silence or a question is not a yes: ask the yes-or-no question again. Otherwise 'false'.",
)
def send_text(
    conv: Conversation,
    flow: Flow,
    use_calling_number: str,
    phone_number: str,
    number_confirmed: str,
):
    sms = _sms(conv)
    if sms["sent_to"]:
        conv.exit_flow()
        return "ALREADY SENT - don't send it again. Ask if there's anything else."
    calling = idnv.normalize_phone(conv.state.caller_phone)

    if str(use_calling_number).strip().lower() == "true" and idnv.is_valid_phone(
        calling
    ):
        if _same_turn_as_question(conv, sms):
            return billing.NOT_DONE_YET
        return _send(conv, sms, calling)

    confirmed = str(number_confirmed).strip().lower() == "true"
    if str(phone_number or "").strip():
        digits = idnv.normalize_phone(phone_number)
        if confirmed and digits and digits == sms["pending"]:
            # Confirmed the number just read back (and repeated it): send, don't read back again.
            if _same_turn_as_question(conv, sms):
                return billing.NOT_DONE_YET
            return _send(conv, sms, digits)
        if not idnv.is_valid_phone(digits):
            sms["retries"] += 1
            conv.state.sms = sms
            if sms["retries"] >= MAX_UNCLEAR:
                return transfer(
                    conv,
                    "SMS_PHONE_NUMBER_COLLECTION_FAIL",
                    "Sorry, that still isn't working. Let me put you through to a colleague, one "
                    "moment please.",
                )
            return (
                f"NOT A FULL NUMBER (attempt {sms['retries']} of {MAX_UNCLEAR}): don't read it "
                "back. Ask for the full ten-digit mobile number, starting with the area code. "
                f"{CALL_AGAIN}"
            )
        sms["pending"] = digits
        sms["asked_turn"] = billing.history_turn(conv)
        conv.state.sms = sms
        return (
            f'READ BACK: ask the caller, in these words: "{number_question(digits)}" Then wait '
            f"for their answer. On a clear yes, call {TOOL} with number_confirmed 'true'; if they "
            f"correct it, call {TOOL} with the full corrected number."
        )

    if confirmed and not sms["pending"]:
        previous = idnv.normalize_phone(conv.state.sms_phone_number)
        if idnv.is_valid_phone(previous):
            sms["pending"] = previous
    if confirmed and sms["pending"]:
        if _same_turn_as_question(conv, sms):
            return billing.NOT_DONE_YET
        return _send(conv, sms, sms["pending"])

    if idnv.is_valid_phone(calling):
        sms["asked_turn"] = billing.history_turn(conv)
        conv.state.sms = sms
        return billing.TEXT_CALLING_NUMBER_OFFER
    return "Ask which mobile number to text. " + CALL_AGAIN
