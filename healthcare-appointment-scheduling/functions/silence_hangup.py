from _gen import *  # <AUTO GENERATED>
from functions.handoff import handoff


@func_description(
    "[Agent Behaviour] Say goodbye and end the call if the user continues to be silent"
)
def silence_hangup(conv: Conversation):
    # If the caller spoke at any point (even vaguely), transfer to Scheduling
    # instead of hanging up — they may need help but can't articulate clearly.
    history = conv.history if hasattr(conv, "history") else None
    caller_spoke = False
    if history:
        for msg in history:
            if getattr(msg, "role", None) == "user" and getattr(msg, "content", ""):
                text = str(msg.content).strip()
                if text and text.lower() not in ("", " "):
                    caller_spoke = True
                    break

    if caller_spoke:
        return handoff(
            conv,
            reason="SPEAK_TO",
            utterance=(
                "I'm having trouble hearing you clearly. "
                "Let me connect you with someone who can help. "
                "Putting you through now."
            ),
        )

    return {
        "utterance": (
            "I'm really sorry, but I still can't hear you. "
            "I'm going to hang up now, but please feel free to call back "
            "when you're ready. Thanks for calling, have a great rest of "
            "your day, goodbye!"
        ),
        "hangup": True,
    }
