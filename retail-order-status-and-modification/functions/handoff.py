from _gen import *  # <AUTO GENERATED>
from functions.utils import (
    hours_not_to_hand,
    opening_hours_utterance,
    variant_opening_hours,
)

# Destinations in config/handoffs.yaml (tests/test_handoff.py checks they match).
DESTINATIONS = ("CUSTOMER_SERVICE",)
DEFAULT_DESTINATION = "CUSTOMER_SERVICE"
DEFAULT_HANDOFF_UTTERANCE = (
    "Please hold the line while I put you through to someone who can help."
)


def _ooh_utterance(conv: Conversation) -> str:
    try:
        hours = opening_hours_utterance(variant_opening_hours(conv))
    except Exception as e:
        hours = ""
        conv.log.warning("Could not build opening hours utterance", error=str(e))
    closed = "I'm sorry, I'll need a colleague to help with that, and we're closed right now."
    if hours:
        return f"{closed} {hours} Please call back then. Thanks for calling, goodbye."
    return (
        f"{closed} {hours_not_to_hand(conv)} Please call back when we're open. "
        "Thanks for calling, goodbye."
    )


@func_description(
    "Transfer the caller to a colleague. Call it whenever you tell the caller you're putting them through."
)
@func_parameter(
    "handoff_reason",
    "The reason code from your instructions, e.g. SPEAK_TO. Copy it exactly.",
)
@func_parameter(
    "handoff_utterance",
    'What to say before transferring. If not given, use "Please hold the line while I put you through to someone who can help."',
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

    conv.state.handoff_reason = reason
    conv.state.handoff_destination = destination
    conv.write_metric("HANDOFF_REASON", reason)
    conv.write_metric("HANDOFF_TO", destination)

    if conv.state.is_ooh:
        conv.write_metric("OUT_OF_HOURS_HANDOFF_REASON", reason)
        return {"utterance": _ooh_utterance(conv), "hangup": True}

    if conv.env in ("sandbox", "draft"):
        conv.log.info("Mock handoff", handoff_reason=reason, handoff_to=destination)
        return {"utterance": utterance, "hangup": True}

    return conv.call_handoff(
        destination=destination, reason=reason, utterance=utterance
    )
