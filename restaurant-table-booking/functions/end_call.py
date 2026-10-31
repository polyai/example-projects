from _gen import *  # <AUTO GENERATED>
from functions import bookings

GOODBYE = "Thanks for calling, enjoy the rest of your day! Goodbye."
CSAT_QUESTION = "Before you go, did you get what you needed from this call today?"


@func_description(
    "The caller has nothing else: end the call. Call it when they say no to 'anything else?' or say goodbye."
)
def end_call(conv: Conversation):
    # settings.csat_enabled (default false; the older top-level csat_enabled also works): ask one satisfaction question before hanging up.
    legacy = bool((conv.real_time_config or {}).get("csat_enabled", False))
    enabled = bookings.is_true(str(bookings.setting(conv, "csat_enabled", legacy)))
    if enabled and not conv.state.csat_asked:
        conv.state.csat_asked = True
        conv.write_metric("CSAT_OFFERED")
        return {
            "utterance": CSAT_QUESTION,
            "content": "When they answer, call log_csat_response.",
        }
    return {"utterance": GOODBYE, "hangup": True}
