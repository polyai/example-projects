import plog
from _gen import *  # <AUTO GENERATED>
from functions.handoff import handoff

_LOG_PREFIX = "[insurance_match_rejected]: "


@func_description("Called when the caller says the matched insurance plan is wrong.")
def insurance_match_rejected(conv: Conversation, flow: Flow) -> dict:
    attempts = (getattr(conv.state, "insurance_collection_attempts", None) or 0) + 1
    conv.state.insurance_collection_attempts = attempts
    conv.write_metric("INSURANCE_MATCH_REJECTED")
    plog.info(f"{_LOG_PREFIX} match rejected; attempt {attempts}")

    if attempts >= 2:
        conv.write_metric("INSURANCE_MATCH_FAILED_MAX_ATTEMPTS")
        return handoff(
            conv,
            reason="INSURANCE_NOT_ACCEPTED",
            utterance=(
                "I'm having trouble matching your insurance plan. "
                "Let me transfer you to our patient accounts team who can help verify your coverage. "
                "Putting you through now."
            ),
        )

    flow.goto_step("Collect Insurance Name")
    return {
        "utterance": (
            "I apologize for the confusion. "
            "Could you tell me your insurance plan name one more time?"
        )
    }
