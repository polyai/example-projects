from _gen import *  # <AUTO GENERATED>
import functions.api_client as api_client
import functions.idnv as idnv
import functions.orders as orders
from functions.handoff import handoff
from functions.start_send_sms import SMS_KEY, ask_calling_number

MAX_UNCLEAR = 3  # numbers that aren't a full number; the last one transfers

# Every return that needs another answer from the caller ends with this, so the model
# passes the next answer to the tool (Dialog-RSN-1 won't repeat a call on its own).
CALL_AGAIN = (
    "Then call send_link again with whatever they say, even if it's the same as before."
)


def _sms(conv) -> dict:
    sms = conv.state.sms
    return (
        dict(sms)
        if isinstance(sms, dict)
        else {
            "template": "store_link",
            "id": "",
            "pending": "",
            "retries": 0,
            "sent_to": "",
        }
    )


def _send(conv, sms: dict, digits: str):
    number = f"+1{digits}"
    if api_client.use_mock_api(conv):
        conv.log.info("Mock SMS (not sent outside live)", template=sms["template"])
        conv.write_metric("SMS_SENT_MOCK", sms.get("id") or sms["template"])
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
                "CUSTOMER_SERVICE",
            )
        conv.write_metric("SMS_SENT", sms.get("id") or sms["template"])
    sms["sent_to"] = digits
    sms["pending"] = ""
    conv.state.sms = sms
    conv.exit_flow()
    return "Sent. Tell the caller the text is on its way (don't read the number again), then ask if there's anything else."


def number_question(digits: str) -> str:
    """What the caller hears before a text goes to a number they gave."""
    return orders.yes_no_question(f"text the link to {idnv.spell_phone(digits)}")


def _read_back(conv, digits: str) -> str:
    orders.asked(conv, SMS_KEY)
    return (
        f"NOT SENT YET. {orders.confirm_instruction(number_question(digits), 'send_link', 'number_confirmed')} "
        "Say the digits exactly as written. If they correct the number, call send_link with the new "
        "number."
    )


def _too_soon(conv) -> bool:
    return orders.same_turn_as_ask(conv, SMS_KEY)


@func_description(
    "Settle the number to text the link to, and send it. Call it whenever the caller answers about the number, even if they repeat the same one."
)
@func_parameter(
    "use_calling_number",
    "'true' only if the caller clearly said yes to texting the number they're calling from, or asked for that themselves. 'Okay', 'mm-hm', silence or a question is not a yes. Otherwise 'false'.",
)
@func_parameter(
    "phone_number",
    "A number the caller gave THIS time, as they said it (words or digits). Never add or guess digits. Empty string if none.",
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
        if _too_soon(conv):
            return orders.wait_for_answer("send_link")
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
                    "CUSTOMER_SERVICE",
                )
            return (
                f"NOT A FULL NUMBER (attempt {sms['retries']} of {MAX_UNCLEAR}): ask for the "
                f"ten-digit mobile number, starting with the area code. {CALL_AGAIN}"
            )
        confirmed = str(number_confirmed).strip().lower() == "true"
        if confirmed and digits == sms["pending"]:
            # A yes to the number this tool asked to read back (repeated with the yes): send.
            if _too_soon(conv):
                return orders.wait_for_answer("send_link")
            return _send(conv, sms, digits)
        sms["pending"] = digits
        conv.state.sms = sms
        return _read_back(conv, digits)

    if str(number_confirmed).strip().lower() == "true" and sms["pending"]:
        if _too_soon(conv):
            return orders.wait_for_answer("send_link")
        return _send(conv, sms, sms["pending"])

    if idnv.is_valid_phone(calling):
        return f"{ask_calling_number(conv)} If they give another number, call send_link with it."
    return "Ask which mobile number to text the link to. " + CALL_AGAIN
