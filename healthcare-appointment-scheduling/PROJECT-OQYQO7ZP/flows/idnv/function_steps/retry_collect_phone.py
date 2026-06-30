from _gen import *  # <AUTO GENERATED>
from functions.handoff import handoff

_MAX_ATTEMPTS = 3


def retry_collect_phone(conv: Conversation, flow: Flow):
    """Increment phone collection attempt counter; handoff at limit or return to Collect Phone Number."""
    attempts = (getattr(conv.state, "idnv_phone_attempts", None) or 0) + 1
    conv.state.idnv_phone_attempts = attempts
    if attempts >= _MAX_ATTEMPTS:
        conv.write_metric("IDNV_PHONE_NOT_COLLECTED")
        return handoff(
            conv,
            reason="IDNV_COLLECTION_FAILED",
            utterance="Let me transfer you to someone who can help verify your account.",
        )
    flow.goto_step("Collect Phone Number", "Retry Phone Number Collection")
    return {"content": "Ask the user to provide their phone number again."}
