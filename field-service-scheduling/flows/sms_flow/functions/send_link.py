from _gen import *  # <AUTO GENERATED>
import functions.api_client as api_client
import functions.idnv as idnv
import functions.visits as visits
from functions.handoff import handoff
from functions.start_send_sms import CALLING_NUMBER_KEY

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
                "I'm sorry, that text didn't go through. Let me put you through to a colleague, "
                "one moment please.",
                "CUSTOMER_CARE",
            )
        conv.write_metric("SMS_SENT", sms["template"])
    sms["sent_to"] = digits
    sms["pending"] = ""
    conv.state.sms = sms
    conv.exit_flow()
    return "Sent. Tell the caller the text is on its way (don't read the number again), then ask if there's anything else."


@func_description("Settle the number to text the link to, and send it.")
@func_parameter(
    "use_calling_number",
    "'true' only if the caller's latest reply was a clear yes to texting the number they're calling from, or they asked for that number themselves. Otherwise 'false'.",
)
@func_parameter(
    "phone_number",
    "A number the caller gave THIS time, as they said it (words or digits) or keyed. Never add or guess digits. Empty string if none.",
)
@func_parameter(
    "number_confirmed",
    "'true' only if the caller's latest reply was a clear yes to the yes-or-no question this tool's readback asked. 'Okay', 'mm-hm', 'sure, whatever', silence or a question is not a yes: ask the yes-or-no question again. Otherwise 'false'.",
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
            return visits.NOT_DONE_YET
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
                    "Sorry, that still isn't working. Let me put you through to a colleague, one "
                    "moment please.",
                    "CUSTOMER_CARE",
                )
            return (
                f"NOT A FULL NUMBER (attempt {sms['retries']} of {MAX_UNCLEAR}): don't read it "
                "back. Ask for the ten-digit mobile number, starting with the area code. "
                + CALL_AGAIN
            )
        confirmed = str(number_confirmed).strip().lower() == "true"
        if confirmed and digits == sms["pending"]:
            # A yes to the number this tool read back, repeated with the yes: send it.
            if visits.same_turn_as_question(conv, READBACK_KEY):
                return visits.NOT_DONE_YET
            return _send(conv, sms, digits)
        sms["pending"] = digits
        conv.state.sms = sms
        visits.mark_question(conv, READBACK_KEY)
        return (
            "NOT SENT YET: in one short question, ask whether to text the link to "
            f'"{idnv.spell_phone(digits)}" (read the number exactly like that), yes or no. Wait '
            "for the answer. If they clearly say yes, call send_link again with "
            "number_confirmed='true'; if they give another number, call send_link with it."
        )

    if str(number_confirmed).strip().lower() == "true" and sms["pending"]:
        if visits.same_turn_as_question(conv, READBACK_KEY):
            return visits.NOT_DONE_YET
        return _send(conv, sms, sms["pending"])

    if idnv.is_valid_phone(calling):
        visits.mark_question(conv, CALLING_NUMBER_KEY)
        return (
            visits.yes_no_question(
                "text the link to the number they're calling from", "Ask"
            )
            + " If they'd rather use another number, ask for it. "
            + CALL_AGAIN
        )
    return "Ask which mobile number to text the link to. " + CALL_AGAIN
