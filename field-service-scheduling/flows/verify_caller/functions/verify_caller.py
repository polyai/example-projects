from _gen import *  # <AUTO GENERATED>
import functions.api_client as api_client
import functions.idnv as idnv
import functions.visits as visits
from functions.handoff import handoff
from functions.start_get_account_number import account_number_instruction

CALLER_ID_QUESTION = "Is the number you're calling from the one on your account?"
FAIL_UTTERANCE = (
    "I'm sorry, I wasn't able to find your account with those details. "
    "Let me put you through to someone who can help. One moment, please."
)
NEW_TO_US = "I'm sorry, I still can't find an account. Are you new to us?"
WELCOME = "Welcome! Let me put you through to our team, who'll get you set up. One moment, please."
NOT_FOUND_LINE = (
    "I'm sorry, I can't find an account under that number. Could you say it again for me, or is "
    "it under a different one?"
)
PARTIAL_LINE = (
    "Sorry, I didn't catch all of that. Could you give me the full number, starting with the "
    "area code?"
)
MISMATCH_LINE = (
    "Sorry, that name doesn't match the account on that number. Could it be under someone else's "
    "name, like a partner's?"
)
NAME_LINE = "Thanks. And what's the full name on the account?"


def _lookup(conv):
    return lambda phone: api_client.find_customers_by_phone(conv, phone)


def _in_our_words(result) -> str:
    """idnv's instruction, with the design's wording for each ask."""
    say = result.say
    if result.outcome == "retry" and "NO ACCOUNT" in say:
        say += f' Say exactly: "{NOT_FOUND_LINE}"'
    elif result.outcome == "retry" and "NOT A FULL NUMBER" in say:
        say = say.replace(
            "Sorry, I didn't catch all of that. Could you say the full number again for me?",
            PARTIAL_LINE,
        )
    elif result.outcome == "retry" and result.missing == ["name"]:
        say += f' Say exactly: "{MISMATCH_LINE}"'
    elif result.outcome == "need" and result.missing == ["name"]:
        say += f' Say: "{NAME_LINE}"'
    return say


@func_description(
    "Find the caller's account from the phone number on it and the account holder's full name. Call it after every answer the caller gives while you're finding their account."
)
@func_parameter(
    "phone_number",
    "The phone number the caller gave THIS time, as they said it (words or digits). Never add, guess or repeat digits. Empty string if they gave no number.",
)
@func_parameter(
    "full_name",
    "The caller's full name as they said it, e.g. 'Jane Doe'. Empty string if not given.",
)
@func_parameter(
    "caller_cannot_verify",
    "'true' only if the caller says they don't have or won't give these details, or that there is no other number to try. Otherwise 'false'.",
)
@func_parameter(
    "phone_confirmed",
    "'true' if the caller's latest reply was a yes, or an acknowledgement, to the question this tool asked: whether the number they're calling from is the one on the account, or that it's the same number after a miss ('it's the same one'). Otherwise 'false'.",
)
@func_parameter(
    "new_customer",
    "'true' if the caller says they're new to us or have never had an account. Otherwise 'false'.",
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
    new_customer: str,
):
    new = str(new_customer or "").strip().lower()
    if new == "true" and not idnv.is_verified(conv):
        conv.write_metric("IDNV_NEW_CUSTOMER")
        return handoff(conv, "NEW_CUSTOMER", WELCOME, "INSIDE_SALES")
    if conv.state.idnv_new_asked:
        # The caller has answered "Are you new to us?" with anything but a yes: the team.
        return handoff(
            conv, idnv.FAILED_REASON_NOT_FOUND, FAIL_UTTERANCE, "CUSTOMER_CARE"
        )

    try:
        result = idnv.verify_lax(
            conv,
            phone_number,
            full_name,
            lookup=_lookup(conv),
            caller_cannot_verify=str(caller_cannot_verify).strip().lower() == "true",
            phone_confirmed=str(phone_confirmed).strip().lower() == "true",
            caller_id_question=CALLER_ID_QUESTION,
        )
    except Exception:
        conv.log.error("verify_caller lookup failed", exc_info=True)
        return handoff(
            conv,
            "API_ERROR",
            "I'm sorry, I'm having trouble finding accounts right now. Let me put you through to "
            "the team. One moment, please.",
            "CUSTOMER_CARE",
        )

    if result.failed:
        if result.handoff_reason == idnv.FAILED_REASON_NOT_FOUND:
            # The second number with no account: ask whether they're new before the team.
            conv.state.idnv_new_asked = True
            return {"utterance": NEW_TO_US}
        return handoff(conv, result.handoff_reason, FAIL_UTTERANCE, "CUSTOMER_CARE")

    if result.verified:
        target = idnv.take_resume(conv)
        first = (result.customer or {}).get("first_name", "")
        conv.state.verified_first_name = first
        conv.state.verified_turn = visits.turn_now(conv)
        thanks = f'Start your reply with "Thanks, {first}."'
        if target == "account_number":
            conv.exit_flow()
            return (
                f"The caller is verified. {thanks} {account_number_instruction(conv)}"
            )
        if target:
            conv.goto_flow(target)
            return (
                f"The caller is verified as {first}. {thanks} Don't ask for anything they have "
                "already told you; carry on with their request in this same reply."
            )
        conv.exit_flow()
        return f"The caller is verified as {first}. {thanks} Then ask how you can help."

    if result.outcome == "wait":
        # idnv's WAIT: called again in the turn the question was asked. Speak it and end the turn, so the
        # model can't loop (on RSN-1 a same-turn loop runs out the turn's budget).
        return {"utterance": result.utterance}

    # The state line first, so idnv's own instruction (ending "call verify_caller again with
    # whatever they say") is the last thing the model reads.
    return f"{idnv.state_line(conv)}.\n{_in_our_words(result)}"
