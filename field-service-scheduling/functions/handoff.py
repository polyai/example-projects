from _gen import *  # <AUTO GENERATED>
from functions.utils import next_opening

DEFAULT_DESTINATION = "CUSTOMER_CARE"
EMERGENCY = "EMERGENCY"

DEFAULT_HANDOFF_UTTERANCE = "Let me put you through to the team. One moment, please."

SKILL_IDS = {
    "INSIDE_SALES": "10000001",
    "CUSTOMER_CARE": "10000002",
    "ACCOUNT_CARE": "10000003",
    "NS_SCHEDULING_INBOUND": "10000004",
    "SPANISH": "10000005",
    "WELCOME_CALL": "10000006",
    "COMMERCIAL": "10000007",
    "BILLING": "10000008",
    "EMERGENCY": "10000009",
}


def _ooh_utterance(conv: Conversation) -> str:
    """The closed-office line: when the office is next open, not the whole week."""
    opening = next_opening(conv)
    again = (
        f" We're open again {opening}, so please give us a call then."
        if opening
        else ""
    )
    return f"I'm sorry, our office is closed right now.{again} Thanks for calling!"


def emergency_destination(conv) -> str:
    """The emergency team takes the transfer at any hour. Until a client gives its number at
    onboarding (settings.emergency_line_configured in real-time config), it goes to customer
    care."""
    settings = (conv.real_time_config or {}).get("settings", {})
    return (
        EMERGENCY
        if settings.get("emergency_line_configured", False)
        else DEFAULT_DESTINATION
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
    'What to say before transferring, ending "One moment, please." If not given, use "Let me put you through to the team. One moment, please."',
)
@func_parameter(
    "handoff_destination",
    "The queue from your instructions, e.g. CUSTOMER_CARE. Use CUSTOMER_CARE if none is given.",
)
def handoff(
    conv: Conversation,
    handoff_reason: str,
    handoff_utterance: str,
    handoff_destination: str,
):
    reason = (handoff_reason or "").strip().upper() or "UNSPECIFIED"
    destination = (handoff_destination or "").strip().upper() or DEFAULT_DESTINATION
    if destination not in SKILL_IDS:
        conv.log.warning(
            "Unknown handoff destination, using default",
            handoff_destination=destination,
            handoff_to=DEFAULT_DESTINATION,
        )
        destination = DEFAULT_DESTINATION
    utterance = handoff_utterance or DEFAULT_HANDOFF_UTTERANCE
    emergency = destination == EMERGENCY
    if emergency:
        destination = emergency_destination(conv)
    skill_id = SKILL_IDS[destination]

    conv.state.handoff_reason = reason
    conv.state.handoff_destination = destination
    conv.state.skill_id = skill_id
    conv.write_metric("HANDOFF_REASON", reason)
    conv.write_metric("HANDOFF_TO", destination)

    if (
        conv.state.is_ooh and not emergency
    ):  # the emergency team takes calls at any hour
        conv.write_metric("OUT_OF_HOURS_HANDOFF_REASON", reason)
        return {"utterance": _ooh_utterance(conv), "hangup": True}

    if conv.env in ("sandbox", "draft"):
        conv.log.info("Mock handoff", handoff_reason=reason, handoff_to=destination)
        return {"utterance": utterance, "hangup": True}

    if conv.state.incontact_id:
        # CXone accepts at most nine signal params (p1-p9)
        return {
            "utterance": utterance,
            "handoff": {
                "type": destination,
                "reason": reason,
                "cxone": {
                    "region": "na1",
                    "domain": "niceincontact",
                    "version": "v24.0",
                    "contactId": conv.state.incontact_id,
                    "signal": {
                        "params": {"p1": destination, "p2": skill_id, "p3": reason}
                    },
                },
            },
        }
    return conv.call_handoff(
        destination=destination, reason=reason, utterance=utterance
    )
