from functions.end_call import GOODBYE

from _gen import *  # <AUTO GENERATED>


@func_description(
    "Log the caller's answer to 'did you get what you needed?' and end the call."
)
@func_parameter(
    "got_what_they_needed", "'true' if they said yes, 'false' if they said no."
)
def log_csat_response(conv: Conversation, got_what_they_needed: str):
    resolved = str(got_what_they_needed).strip().lower() == "true"
    conv.write_metric("CSAT_RESPONSE", "YES" if resolved else "NO")
    return {"utterance": GOODBYE, "hangup": True}
