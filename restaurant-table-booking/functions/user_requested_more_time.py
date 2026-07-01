from _gen import *  # <AUTO GENERATED>


@func_description(
    "Call when user explicitly requested you to wait for them, or was silent after you told him you are happy to wait. Do not call it if the agent requested time, or if user is silent without telling agent they need some time first."
)
def user_requested_more_time(conv: Conversation):
    # determine if user was silent this turn
    user_silent = False
    for event in conv.history[::-1]:
        if event.role == "user":
            user_silent = not bool(event.text)
            break

    if not user_silent:
        conv.state.user_requested_wait = True
        utterance = "Sure, let me know when you're ready."
    else:
        if not conv.state.user_requested_wait:
            return """user_requested_time was called without user indicating they wanted time. Follow prompts under SILENCE BEHAVIOR instead of calling this function.
      If the user goes silent without previously indicating they need some time, say these in order (omit this behavior if the user asked if you can hear them):
        - "Umm, are you still there?"
        - "Hi, are you still on the line?"
        If you still can't hear anything say: "I can't hear anything from your end but I'll be here whenever you're ready, give us a call back any time. Goodbye"
      """
        utterance = "Take your time"
    return {"utterance": utterance, "listen": {"asr": {"timeout": 20}}}
