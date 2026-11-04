from _gen import *  # <AUTO GENERATED>
from functions.handoff import handoff

SPOKE_UTTERANCE = (
    "I'm sorry, I can't hear you. I'll put you through to our clinical team, who can help. One "
    "moment, please."
)
NEVER_SPOKE_UTTERANCE = (
    "I'm sorry, I can't hear anything, so I'll end the call now. Please call back whenever "
    "you're ready. Take care!"
)


@func_description(
    "[Agent Behaviour] The caller has stayed silent after you asked again: end the call, or put them through if they spoke earlier."
)
def silence_hangup(conv: Conversation):
    # In a clinic, a caller who spoke and then goes silent may be unwell: they go to the
    # clinical team (a healthcare exception to the platform's silence hang-up).
    caller_spoke = False
    for msg in getattr(conv, "history", None) or []:
        if (
            getattr(msg, "role", None) == "user"
            and str(getattr(msg, "content", "") or "").strip()
        ):
            caller_spoke = True
            break
    if caller_spoke:
        return handoff(conv, "SILENCE_AFTER_SPEECH", SPOKE_UTTERANCE)
    return {"utterance": NEVER_SPOKE_UTTERANCE, "hangup": True}
