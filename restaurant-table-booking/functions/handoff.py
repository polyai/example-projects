from _gen import *  # <AUTO GENERATED>
from functions import bookings, hours

DESTINATION = "RESTAURANT"  # config/handoffs.yaml
MOCK_ENVS_EXCLUDED = ("pre-release", "pre_release", "live")

DEFAULT_UTTERANCE = "Sure, I'll put you through to the team. One moment please."
OUT_OF_HOURS_UTTERANCE = (
    "We're closed right now, but I'll put you through so you can leave a voicemail, and the team "
    "will get back to you as soon as they can. One moment please."
)


def restaurant_open_now(conv) -> bool:
    return hours.is_open_at(conv, bookings.now(conv))


@func_description(
    "Put the caller through to the restaurant team. Call it whenever you tell the caller you're putting them through, in the same turn."
)
@func_parameter(
    "handoff_reason",
    "The reason code from your instructions, e.g. SPEAK_TO. Copy it exactly.",
)
@func_parameter(
    "handoff_utterance",
    'What to say before transferring. Empty string to use "Sure, I\'ll put you through to the team. One moment please."',
)
def handoff(conv: Conversation, handoff_reason: str, handoff_utterance: str):
    reason = (handoff_reason or "").strip().upper() or "UNSPECIFIED"
    utterance = (handoff_utterance or "").strip() or DEFAULT_UTTERANCE
    conv.state.handoff_reason = reason
    conv.write_metric("HANDOFF_REASON", reason)
    conv.write_metric("HANDOFF_TO", DESTINATION)

    if not restaurant_open_now(conv):
        conv.write_metric("OUT_OF_HOURS_HANDOFF_REASON", reason)
        # settings.transfer_out_of_hours (default true): transfer to voicemail when closed.
        if not bookings.is_true(
            str(bookings.setting(conv, "transfer_out_of_hours", True))
        ):
            if conv.current_flow:
                conv.exit_flow()
            return (
                "The restaurant is closed right now, so you can't put the caller through. Tell "
                "them that, give today's opening hours if you know them, and ask if there's "
                "anything else you can help with."
            )
        utterance = OUT_OF_HOURS_UTTERANCE

    if (conv.env or "").lower() not in MOCK_ENVS_EXCLUDED:
        conv.log.info("Mock handoff", handoff_reason=reason, handoff_to=DESTINATION)
        return {"utterance": utterance, "hangup": True}
    return conv.call_handoff(
        destination=DESTINATION, reason=reason, utterance=utterance
    )
