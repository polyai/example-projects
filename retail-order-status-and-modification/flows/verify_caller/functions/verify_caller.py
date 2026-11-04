from _gen import *  # <AUTO GENERATED>
import re

import functions.api_client as api_client
import functions.idnv as idnv
import functions.orders as orders
from functions.handoff import handoff

FAIL_UTTERANCE = (
    "I'm sorry, I wasn't able to find your account with those details. I'll put you through to "
    "the team, who can help. One moment, please."
)
LOOKUP_DOWN_UTTERANCE = (
    "I'm sorry, I'm having trouble looking up accounts right now. I'll put you through to the "
    "team, who can help. One moment, please."
)
NAME_ASK = "Thanks. And what's your full name?"
NAME_MISMATCH = (
    "Sorry, I can't match that name to the account on that number. Could the account be under "
    "someone else's name?"
)
NOT_FOUND = (
    "I'm sorry, I can't find an account under that number. Could you say it again for me, or is "
    "it under a different one?"
)
PARTIAL = "Sorry, I only caught part of that. What's the full number, starting with the area code?"
NUMBER_ASK = "What's the phone number on your account?"
_HEAD = re.compile(r"^([A-Z][A-Z ]+ \(attempt \d+ of \d+\)): ")


def _lookup(conv):
    return lambda phone: api_client.find_customers_by_phone(conv, phone)


def _worded(result) -> str:
    """idnv's return with this template's wording for the lines the caller hears. idnv keeps
    the attempt counts, the call-again line and the rules; only the spoken line changes."""
    say = result.say
    head = _HEAD.match(say)
    label = head.group(1) if head else ""
    if label.startswith("NO ACCOUNT"):
        return (
            f'{label}: nothing is under that number. Say: "{NOT_FOUND}" Never read the number back. '
            "If they say it's the same number, pass phone_confirmed='true' and no phone number; if "
            "they give a number, pass it, even if it's the same. If they say there isn't another "
            f"one, call verify_caller with caller_cannot_verify='true'. {idnv.CALL_AGAIN}"
        )
    if label.startswith("NOT VERIFIED"):
        return (
            f"{label}: that name doesn't match the account on that number. Kept: the phone number, "
            f'so don\'t ask for it again. Say: "{NAME_MISMATCH}" Pass only the name they give now. '
            f"Never say or hint at the name on file. {idnv.CALL_AGAIN}"
        )
    if label.startswith("NOT A FULL NUMBER"):
        return (
            f'{label}: that wasn\'t a full phone number. Say: "{PARTIAL}" Never repeat the digits '
            f"they said. {idnv.CALL_AGAIN}"
        )
    if result.outcome == "need" and result.missing == ["name"]:
        return (
            f'Say: "{NAME_ASK}" Don\'t say whether you found an account or whose it is. '
            f"{idnv.CALL_AGAIN}"
        )
    if say.startswith("Ask for the phone number on their account"):
        return f'Ask: "{NUMBER_ASK}" {idnv.CALL_AGAIN}'
    return say


@func_description(
    "Check who the caller is from the phone number on their account and their full name. Call it whenever the caller gives either one, or answers a question this tool asked, even if it's the same as before."
)
@func_parameter(
    "phone_number",
    "The phone number the caller gave THIS time, as they said it (words or digits). Never add, guess or repeat digits. Empty string if they gave no number.",
)
@func_parameter(
    "full_name",
    "The caller's full name as they said it, e.g. 'John Smith'. Empty string if not given.",
)
@func_parameter(
    "caller_cannot_verify",
    "'true' only if the caller says they don't have or won't give these details, or that there is no other number to try. Otherwise 'false'.",
)
@func_parameter(
    "phone_confirmed",
    "'true' when the caller's latest reply is a yes, or an acknowledgement ('okay', 'sure', 'yeah'), to the question this tool asked: whether the number they're calling from is the one on their account, or, after a miss, that it's the same one they gave. Otherwise 'false'.",
)
@func_latency_control(
    delay_before_responses_start=1,
    silence_after_each_response=3,
    delay_responses=[
        ("One moment while I find your account.", 3),
        ("Nearly there.", 3),
    ],
)
def verify_caller(
    conv: Conversation,
    flow: Flow,
    phone_number: str,
    full_name: str,
    caller_cannot_verify: str,
    phone_confirmed: str,
):
    try:
        result = idnv.verify_lax(
            conv,
            phone_number,
            full_name,
            lookup=_lookup(conv),
            caller_cannot_verify=str(caller_cannot_verify).strip().lower() == "true",
            phone_confirmed=str(phone_confirmed).strip().lower() == "true",
            caller_id_question=orders.CALLER_ID_QUESTION,
        )
    except Exception:
        conv.log.error("verify_caller lookup failed", exc_info=True)
        return handoff(conv, "API_ERROR", LOOKUP_DOWN_UTTERANCE, "CUSTOMER_SERVICE")

    if result.failed:
        return handoff(conv, result.handoff_reason, FAIL_UTTERANCE, "CUSTOMER_SERVICE")

    if result.outcome == "wait":
        # idnv WAIT: called again in the turn it asked a question: speak the question and end the turn,
        # so RSN-1 can't loop on the tool until the turn's budget runs out.
        return {"utterance": result.utterance}

    if result.verified:
        s = idnv.state(conv)
        # The first name only when the caller gave the account holder's name first time: after
        # a mismatch the name may be someone else's (a husband's account).
        first = (
            (result.customer or {}).get("first_name", "") if not s["mismatches"] else ""
        )
        thanks = f"Thanks, {first}." if first else "Thanks."
        target = idnv.take_resume(conv)
        if target:
            conv.goto_flow(target)
            return (
                f'The caller is verified. Start your reply with "{thanks}" and carry on with their '
                "request in this same reply. Don't use their name again, and don't ask for "
                "anything they've already told you."
            )
        conv.exit_flow()
        return f'The caller is verified. Say "{thanks}" and ask how you can help.'

    return _worded(result)
