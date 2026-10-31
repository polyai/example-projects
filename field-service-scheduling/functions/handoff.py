from _gen import *  # <AUTO GENERATED>
from functions.utils import HOURS_NOT_TO_HAND, site_hours_utterance, variant_attr

DEFAULT_DESTINATION = "CUSTOMER_CARE"

DEFAULT_HANDOFF_UTTERANCE = (
    "Please hold the line while I put you through to a colleague who can help."
)

SKILL_IDS = {
    "INSIDE_SALES": "10000001",
    "CUSTOMER_CARE": "10000002",
    "ACCOUNT_CARE": "10000003",
    "NS_SCHEDULING_INBOUND": "10000004",
    "SPANISH": "10000005",
    "WELCOME_CALL": "10000006",
    "COMMERCIAL": "10000007",
    "BILLING": "10000008",
}


def _ooh_utterance(conv: Conversation) -> str:
    hours = site_hours_utterance(conv) or HOURS_NOT_TO_HAND
    phone = variant_attr(conv, "phone_number")
    call_back = f" You can call us back on {phone}." if phone else ""
    return (
        "I'm sorry, I'll need a colleague to help with that, and our office is closed right now."
        f" {hours}{call_back} Thanks for calling, goodbye."
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
    'What to say before transferring. If not given, use "Please hold the line while I put you through to a colleague who can help."',
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
    skill_id = SKILL_IDS[destination]

    conv.state.handoff_reason = reason
    conv.state.handoff_destination = destination
    conv.state.skill_id = skill_id
    conv.write_metric("HANDOFF_REASON", reason)
    conv.write_metric("HANDOFF_TO", destination)

    if conv.state.is_ooh:
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
