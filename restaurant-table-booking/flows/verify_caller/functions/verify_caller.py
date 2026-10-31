from _gen import *  # <AUTO GENERATED>
import functions.api_client as api_client
import functions.idnv as idnv
from functions.handoff import handoff

FAIL_UTTERANCE = (
    "I'm sorry, I wasn't able to find your booking with those details. Let me put you through to "
    "the team, who can help. One moment please."
)
# The number was never confirmed (unclear digits, or no clear yes to the readback):
# nothing was looked up against a confirmed number, so don't say no booking was found.
UNCONFIRMED_UTTERANCE = (
    "I'm sorry, I wasn't able to confirm your number. Let me put you through to the team, who "
    "can help. One moment please."
)
# Reasons that mean "no booking found" rather than "wrong details": offer a new booking.
NO_BOOKING_REASONS = (idnv.FAILED_REASON_NOT_FOUND, idnv.FAILED_REASON_DECLINED)


def _lookup(conv):
    return lambda phone: api_client.find_guests_by_phone(conv, phone)


@func_description(
    "Find who the caller is from the phone number their booking is under and the name on it. Call it whenever the caller gives either one, or answers or corrects a number you read back."
)
@func_parameter(
    "phone_number",
    "The phone number the caller gave THIS time, as they said it (words or digits). Never add, guess or repeat digits. Empty string if they gave no number.",
)
@func_parameter(
    "full_name",
    "The name the booking is under as they said it, e.g. 'John Smith'. Empty string if not given.",
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
        ("One moment while I find your booking.", 3),
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
    # A caller still reading out part of a number hasn't given up, whatever the flag says.
    cannot_verify = str(caller_cannot_verify).strip().lower() == "true"
    digits = idnv.normalize_phone(phone_number)
    if cannot_verify and digits and not idnv.is_valid_phone(digits):
        cannot_verify = False
    try:
        result = idnv.verify_lax(
            conv,
            phone_number,
            full_name,
            lookup=_lookup(conv),
            caller_cannot_verify=cannot_verify,
            phone_confirmed=str(phone_confirmed).strip().lower() == "true",
        )
    except Exception:
        conv.log.error("verify_caller lookup failed", exc_info=True)
        return handoff(
            conv,
            "API_ERROR",
            "I'm sorry, I'm having trouble looking up bookings right now. Let me put you through "
            "to the team. One moment please.",
        )

    if result.failed:
        if result.handoff_reason in NO_BOOKING_REASONS:
            idnv.take_resume(conv)
            conv.exit_flow()
            conv.write_metric("NO_BOOKING_FOUND", result.handoff_reason)
            told = (
                "you couldn't find a booking under that number"
                if result.handoff_reason == idnv.FAILED_REASON_NOT_FOUND
                else "you can't look up a booking without those details"
            )
            return (
                f'Tell the caller {told}, and ask: "Would '
                'you like to make a new booking, or shall I put you through to the team?" New '
                "booking: call start_make_booking. The team, or an answer that doesn't pick one "
                "(like 'okay' or 'yes'): call handoff with handoff_reason=NO_BOOKING_FOUND. Don't "
                "ask the question again."
            )
        if result.handoff_reason == idnv.FAILED_REASON_UNCLEAR:
            return handoff(conv, result.handoff_reason, UNCONFIRMED_UTTERANCE)
        return handoff(conv, result.handoff_reason, FAIL_UTTERANCE)

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

    if result.say.startswith("WAIT:"):
        # A repeat call in the turn the number was read back (the caller hasn't answered):
        # on RSN-1 the model kept calling here until the turn failed. Speak the readback,
        # which ends the tool loop; nothing is counted or confirmed.
        return {"utterance": f"Is that {idnv.spell_phone(idnv.state(conv)['phone'])}?"}
    # idnv's say ends with the instruction to call verify_caller again: pass it through whole.
    return f"{result.say}\n\n{idnv.state_line(conv)}"
