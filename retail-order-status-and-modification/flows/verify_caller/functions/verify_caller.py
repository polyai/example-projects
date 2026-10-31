from _gen import *  # <AUTO GENERATED>
import functions.api_client as api_client
import functions.idnv as idnv
from functions.handoff import handoff

FAIL_UTTERANCE = (
    "I'm sorry, I wasn't able to find your account with those details. "
    "Let me put you through to a colleague who can help. One moment please."
)


def _lookup(conv):
    return lambda phone: api_client.find_customers_by_phone(conv, phone)


@func_description(
    "Check who the caller is from the phone number on their account and their full name. Call it whenever the caller gives either one, or confirms or corrects a number you read back, even if it's the same as before."
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
    "'true' only if, in their latest reply, the caller clearly said yes to the phone number this tool told you to read back, or repeated that same number. An \"okay\", or anything unclear, is not a yes. Otherwise 'false'.",
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
        )
    except Exception:
        conv.log.error("verify_caller lookup failed", exc_info=True)
        return handoff(
            conv,
            "API_ERROR",
            "I'm sorry, I'm having trouble looking up accounts right now. "
            "Let me put you through to a colleague. One moment please.",
            "CUSTOMER_SERVICE",
        )

    if result.failed:
        return handoff(conv, result.handoff_reason, FAIL_UTTERANCE, "CUSTOMER_SERVICE")

    if result.verified:
        target = idnv.take_resume(conv)
        first = (result.customer or {}).get("first_name", "")
        if target:
            conv.goto_flow(target)
            return (
                f"The caller is verified as {first}. Don't ask for anything they have already "
                "told you; carry on with their request in this same reply."
            )
        conv.exit_flow()
        return f"The caller is verified as {first}. Ask how you can help."

    if result.outcome == "read_back" and result.say.startswith("WAIT"):
        # A second call in the turn that read the number back: the caller hasn't answered yet.
        # Say the readback and end the turn here, so the model can't keep calling (on RSN-1 a
        # same-turn loop runs out the turn's steps and the turn errors).
        return {"utterance": readback_question(conv)}

    # idnv's say ends with the instruction to call verify_caller again: pass it on whole.
    return result.say


def readback_question(conv) -> str:
    return (
        f"Just to check, is your number {idnv.spell_phone(idnv.state(conv)['phone'])}?"
    )
