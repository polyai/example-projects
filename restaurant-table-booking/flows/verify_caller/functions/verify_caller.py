from _gen import *  # <AUTO GENERATED>
import functions.api_client as api_client
import functions.bookings as bookings
import functions.idnv as idnv
from functions.handoff import handoff

FAIL_UTTERANCE = (
    "I'm sorry, I wasn't able to find your booking with those details. Let me put you through to "
    "the team, who can help. One moment, please."
)
UNCLEAR_UTTERANCE = (
    "I'm sorry, I'm having trouble catching the number. Let me put you through to the team, who "
    "can help. One moment, please."
)
NOT_FOUND_UTTERANCE = (
    "I'm sorry, I still can't find a booking under that number. Would you like to make a new one, "
    "or shall I put you through to the team?"
)
DECLINED_UTTERANCE = (
    "No problem. I can't look up a booking without those details, I'm afraid. Would you like to "
    "make a new one, or shall I put you through to the team?"
)


def _lookup(conv):
    return lambda phone: api_client.find_guests_by_phone(conv, phone)


@func_description(
    "Find the caller's booking from the phone number it's under and the name on it. Call it whenever the caller gives either one, or answers a question this tool told you to ask."
)
@func_parameter(
    "phone_number",
    "The phone number the caller gave THIS time, as they said it (words or digits). Never add, guess or repeat digits. Empty string if they gave no number.",
)
@func_parameter(
    "full_name",
    "The name the booking is under as they said it, e.g. 'Jane Doe'. Empty string if not given.",
)
@func_parameter(
    "caller_cannot_verify",
    "'true' only if the caller says they don't have or won't give these details, or that there is no other number to try. Otherwise 'false'.",
)
@func_parameter(
    "phone_confirmed",
    "'true' if the caller said yes, or an acknowledgement ('okay', 'sure', 'yeah'), to the question this tool asked: whether the booking is under the number they're calling from, or, after a miss, that it's the same number. Otherwise 'false'.",
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
            caller_id_question=bookings.CALLER_ID_QUESTION,
        )
    except Exception:
        conv.log.error("verify_caller lookup failed", exc_info=True)
        return handoff(
            conv,
            "API_ERROR",
            "I'm sorry, I'm having trouble looking up bookings right now. Let me put you through "
            "to the team. One moment, please.",
        )

    if result.failed:
        if result.handoff_reason in (
            idnv.FAILED_REASON_NOT_FOUND,
            idnv.FAILED_REASON_DECLINED,
        ):
            idnv.take_resume(conv)
            conv.exit_flow()
            conv.write_metric("NO_BOOKING_FOUND", result.handoff_reason)
            said = (
                NOT_FOUND_UTTERANCE
                if result.handoff_reason == idnv.FAILED_REASON_NOT_FOUND
                else DECLINED_UTTERANCE
            )
            return {
                "utterance": said,
                "content": (
                    "A new booking: call start_make_booking. The team, or an answer that doesn't "
                    "pick one: call handoff with handoff_reason=NO_BOOKING_FOUND. Don't ask again."
                ),
            }
        if result.handoff_reason == idnv.FAILED_REASON_UNCLEAR:
            return handoff(conv, result.handoff_reason, UNCLEAR_UTTERANCE)
        return handoff(conv, result.handoff_reason, FAIL_UTTERANCE)

    if result.verified:
        target = idnv.take_resume(conv)
        first = (result.customer or {}).get("first_name", "")
        if target:
            conv.goto_flow(target)
            return (
                f"The caller is verified as {first}. Thank them by first name once, don't ask for "
                "anything they have already told you, and carry on with their request in this "
                "same reply."
            )
        conv.exit_flow()
        return f"The caller is verified as {first}. Ask how you can help."

    if result.outcome == "wait":
        # idnv's WAIT: called again in the turn a question was asked (the caller hasn't answered): on
        # RSN-1 the model kept calling here until the turn failed. Speak the question,
        # which ends the tool loop; nothing is counted or confirmed.
        return {"utterance": result.utterance}
    # idnv's say ends with the instruction to call verify_caller again: pass it through whole.
    return f"{bookings.booking_words(result.say)}\n\n{idnv.state_line(conv)}"
