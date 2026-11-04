from _gen import *  # <AUTO GENERATED>
from functions.utils import hours_not_to_hand, next_opening, variant_opening_hours

# Destinations in config/handoffs.yaml (tests/test_handoff.py checks they match).
DESTINATIONS = ("CUSTOMER_SERVICE",)
DEFAULT_DESTINATION = "CUSTOMER_SERVICE"
DEFAULT_HANDOFF_UTTERANCE = "I'll put you through to the team now. One moment, please."
CLOSED_LEAD = "I'm sorry, the team isn't available right now."
CLOSED_TAIL = "Is there anything else I can help with in the meantime?"


def ooh_utterance(conv) -> str:
    """When the team is closed and the caller needs a person: when they're back (the next
    opening time, not the whole week), then the anything-else question. No transfer, and the
    call carries on."""
    try:
        back = next_opening(conv, variant_opening_hours(conv))
    except Exception as e:
        back = ""
        conv.log.warning("Could not work out the next opening time", error=str(e))
    if back:
        return f"{CLOSED_LEAD} They're back at {back}, so please give us a call then. {CLOSED_TAIL}"
    return f"{CLOSED_LEAD} {hours_not_to_hand(conv)} {CLOSED_TAIL}"


@func_description(
    "Transfer the caller to the team. Call it whenever you tell the caller you're putting them through."
)
@func_parameter(
    "handoff_reason",
    "The reason code from your instructions, e.g. SPEAK_TO. Copy it exactly.",
)
@func_parameter(
    "handoff_utterance",
    'What to say before transferring, from your instructions. If none is given, use "I\'ll put you through to the team now. One moment, please."',
)
@func_parameter(
    "handoff_destination",
    "The queue from your instructions. Use CUSTOMER_SERVICE if none is given.",
)
def handoff(
    conv: Conversation,
    handoff_reason: str,
    handoff_utterance: str,
    handoff_destination: str,
):
    reason = (handoff_reason or "").strip().upper() or "UNSPECIFIED"
    destination = (handoff_destination or "").strip().upper() or DEFAULT_DESTINATION
    if destination not in DESTINATIONS:
        conv.log.warning(
            "Unknown handoff destination, using default",
            handoff_destination=destination,
            handoff_to=DEFAULT_DESTINATION,
        )
        destination = DEFAULT_DESTINATION
    utterance = handoff_utterance or DEFAULT_HANDOFF_UTTERANCE

    if conv.state.is_ooh:
        conv.write_metric("OUT_OF_HOURS_HANDOFF_REASON", reason)
        return {"utterance": ooh_utterance(conv)}

    conv.state.handoff_reason = reason
    conv.state.handoff_destination = destination
    conv.write_metric("HANDOFF_REASON", reason)
    conv.write_metric("HANDOFF_TO", destination)

    if conv.env in ("sandbox", "draft"):
        conv.log.info("Mock handoff", handoff_reason=reason, handoff_to=destination)
        return {"utterance": utterance, "hangup": True}

    return conv.call_handoff(
        destination=destination, reason=reason, utterance=utterance
    )
