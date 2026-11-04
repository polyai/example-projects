from _gen import *  # <AUTO GENERATED>
import functions.api_client as api_client
import functions.billing as billing
import functions.idnv as idnv
from functions.handoff import transfer
from functions.start_send_sms import (
    ACCOUNT_NUMBER_QUESTION,
    ACCOUNT_TEMPLATES,
    ALREADY_SENT,
    account_number,
    ask,
    calling_number,
    first_question,
    fresh,
)

MAX_UNCLEAR = 3  # numbers that aren't a full phone number before the transfer
TOOL = "send_text"
CALL_AGAIN = (
    f"Then call {TOOL} again with whatever number they say, as they said it, even if it's the same "
    "or sounds incomplete. Read back only what this tool returns."
)
OTHER_NUMBER_QUESTION = "What number should I send it to?"
SENT = "I've sent that over to you now. It may take a minute to arrive. Is there anything else I can help with?"
SENT_CONFIRMATION = (
    "I've sent your confirmation over now. Is there anything else I can help with?"
)
CONFIRMATION_ONLY_OURS = (
    "I'm afraid I can only text a confirmation to the number you're calling from or the one on "
    "your account. I can read the confirmation number out again, if that helps."
)


def number_question(digits: str) -> str:
    """The readback of a number the caller gave, then the question."""
    return f"That's {idnv.spell_phone(digits)}. Shall I send it there?"


def _sms(conv) -> dict:
    sms = conv.state.sms
    return dict(sms) if isinstance(sms, dict) else fresh("")


def _same_turn(conv, sms: dict) -> bool:
    """The question was asked in this same turn (history length unchanged), so the caller can't
    have answered it yet. The length is a marker only."""
    turn = billing.history_turn(conv)
    return (
        turn is not None
        and sms.get("asked_turn") is not None
        and turn == sms["asked_turn"]
    )


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
            conv.exit_flow()
            return (
                "The text didn't go through. Say you're sorry, you couldn't send it, give the one "
                "or two steps out loud instead, and ask if there's anything else."
            )
        conv.write_metric("SMS_SENT", sms["template"])
    sms.update(sent_to=digits, pending="", offered="")
    conv.state.sms = sms
    if sms["template"] not in ACCOUNT_TEMPLATES:
        conv.state.sms_phone_number = digits
    sent = conv.state.sms_sent if isinstance(conv.state.sms_sent, list) else []
    conv.state.sms_sent = sent + [sms["template"]]
    conv.exit_flow()
    return {
        "utterance": SENT_CONFIRMATION if sms["template"] in ACCOUNT_TEMPLATES else SENT
    }


def _confirmation_elsewhere(conv) -> str:
    conv.exit_flow()
    spoken = conv.state.last_confirmation_spoken or billing.say_digits(
        conv.state.last_confirmation_number
    )
    return (
        f'Say: "{CONFIRMATION_ONLY_OURS}" If they\'d like that, say: "It\'s {spoken}." a little '
        "slower, then ask if there's anything else."
    )


@func_description(
    "Settle the number to text and send the message. Pass every answer to this tool's question: a yes or a no, or a number as they said it, even if it sounds incomplete. It checks the number and returns the readback; never read a number back before it returns."
)
@func_parameter(
    "use_calling_number",
    "'true' only if the caller's latest reply agreed to this tool's question about the number they're calling from. A yes, 'okay', 'sure' or 'go on' to that question is agreement; an answer to something else, or real hesitation, is not. Otherwise 'false'.",
)
@func_parameter(
    "phone_number",
    "A number the caller gave THIS time, as they said it (words or digits), even if it sounds incomplete. Apply a partial correction to the number read back and pass the full number. Never add or guess digits.",
)
@func_parameter(
    "number_confirmed",
    "'true' only if the caller's latest reply agreed to the readback question this tool returned (\"Shall I send it there?\", or the same number as before, or the number on their account). A yes, 'okay', 'sure' or 'go on' to that question is agreement; an answer to something else, or real hesitation, is not. Otherwise 'false'.",
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
        return {"utterance": ALREADY_SENT}
    confirmation = sms["template"] in ACCOUNT_TEMPLATES
    calling = calling_number(conv)
    yes = (
        str(use_calling_number).strip().lower() == "true"
        or str(number_confirmed).strip().lower() == "true"
    )
    said = str(phone_number or "").strip()
    digits = idnv.normalize_phone(said) if said else ""

    if said and not digits and not yes:
        # Words with no digits ("it's my cell...") are not an attempt.
        return f'Say "Go ahead" and wait for the number. {CALL_AGAIN}'
    if said and digits and not (yes and digits == sms["pending"]):
        if confirmation:
            if digits in (calling, account_number(conv)):
                # The number on the account, or the one they're calling from, said out loud: it
                # answers the question. It's an ID&V number, so it isn't read back.
                if _same_turn(conv, sms):
                    return billing.NOT_DONE_YET
                return _send(conv, sms, digits)
            return _confirmation_elsewhere(conv)
        if not idnv.is_valid_phone(digits):
            sms["retries"] += 1
            conv.state.sms = sms
            if sms["retries"] >= MAX_UNCLEAR:
                return transfer(
                    conv,
                    "SMS_PHONE_NUMBER_COLLECTION_FAIL",
                    "I'm sorry, I'm still not getting that. I'll put you through to a colleague "
                    "who can help. One moment, please.",
                )
            return (
                f"NOT A FULL NUMBER (attempt {sms['retries']} of {MAX_UNCLEAR}): don't read it "
                "back. Say: \"Sorry, I didn't catch all of that. Could you give me the full "
                'number, starting with the area code?" ' + CALL_AGAIN
            )
        sms.update(
            pending=digits, offered="number", asked_turn=billing.history_turn(conv)
        )
        conv.state.sms = sms
        return (
            f'READ BACK: say, in these words: "{number_question(digits)}" Then wait for their '
            f"answer. A yes, or an acknowledgement, to that question → call {TOOL} with "
            f"number_confirmed 'true'. A corrected number → call {TOOL} with the full corrected "
            "number."
        )

    if yes:
        if (
            str(use_calling_number).strip().lower() == "true"
            and calling
            and not sms["pending"]
        ):
            sms["pending"] = calling
        if sms["pending"]:
            if _same_turn(conv, sms):
                return billing.NOT_DONE_YET
            return _send(conv, sms, sms["pending"])
        return first_question(conv, sms)

    # A no, or an answer that isn't a yes.
    if _same_turn(conv, sms):
        return billing.NOT_DONE_YET
    if sms["offered"] == "caller_id" and confirmation:
        account = account_number(conv)
        if account and account != calling:
            return ask(conv, sms, "account", ACCOUNT_NUMBER_QUESTION, account)
        return _confirmation_elsewhere(conv)
    if sms["offered"] == "account":
        return _confirmation_elsewhere(conv)
    if sms["offered"] in ("caller_id", "previous", "number"):
        sms.update(offered="ask", pending="", asked_turn=billing.history_turn(conv))
        conv.state.sms = sms
        return f'Ask: "{OTHER_NUMBER_QUESTION}" {CALL_AGAIN}'
    if not sms["offered"]:
        return first_question(conv, sms)
    return (
        "If they no longer want the text, say that's fine and ask if there's anything else. If "
        "they don't have a mobile, give the one or two steps out loud, or point them to our "
        f"website. Otherwise ask for the mobile number to send it to. {CALL_AGAIN}"
    )
