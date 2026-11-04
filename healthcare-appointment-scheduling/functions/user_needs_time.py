from _gen import *  # <AUTO GENERATED>


@func_description(
    "[Agent Behaviour] Call when the caller asks you to wait ('hang on', 'let me find my card'), or stays silent after you said you're happy to wait. Not when you need time yourself."
)
def user_needs_time(conv: Conversation):
    conv.write_metric("USER_REQUESTED_TIME", True)

    # Was the caller silent this turn?
    user_silent = False
    for event in conv.history[::-1]:
        if event.role == "user":
            user_silent = not bool(event.text)
            break

    if not user_silent:
        conv.state.user_requested_wait = True
        utterance = "No problem, take your time."
    else:
        if not conv.state.user_requested_wait:
            return (
                "user_needs_time was called but the caller didn't ask for time. Say your last "
                "question again, shorter."
            )
        utterance = ""

    return {"utterance": utterance, "listen": {"asr": {"timeout": 20}}}
