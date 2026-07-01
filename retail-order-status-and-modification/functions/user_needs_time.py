from _gen import *  # <AUTO GENERATED>

from .utterances import utterance


@func_description(
    "[Agent Behaviour] Call when user explicitly requested you to wait for them, or was silent after you told them you are happy to wait. Do not call it if the agent requested time, or if user has not requested time."
)
@func_parameter("times_called", "number of times this function has been called")
def user_needs_time(conv: Conversation, times_called: int):
    if conv.state.wait_counter is None:
        conv.state.wait_counter = 0

    conv.state.wait_counter += 1

    if conv.state.wait_counter == 1:
        return {
            "utterance": utterance(conv, "wait_acknowledge"),
            "listen": {"asr": {"timeout": 20}},
        }
    elif (conv.state.wait_counter - 1) % 2 == 0:
        # Every third turn *after* the first utterance
        return """Let the user know that you're still waiting for them, with the appropriate context - e.g., you're still waiting for their order number. Say something like, "I'm here whenever you're ready"""
    else:
        return {"utterance": "", "listen": {"asr": {"timeout": 20}}}

    # Determine if user was silent this turn


#   user_silent = False
#   for event in conv.history[::-1]:
#       if event.role == "user":
#           user_silent = not bool(event.text)
#           break

#   # If user not silent, they requested time. Return wait behaviour prompt, and flag this
#   if not user_silent:
#       conv.state.user_requested_wait = True
#       utterance = "Sure, just let me know when you're ready."
#   else:
#       # If user silent and hasn't requested time, prompt for silence behaviour
#       # Ideally this should not happen
#       if not conv.state.user_requested_wait:
#           return "user_requested_time called without user indicating they wanted time. Follow prompts under SILENCE BEHAVIOR instead of calling this function."

#       # If user silent but has requested time, return silence
#       utterance = ""

#   return {"utterance": utterance, "listen": {"asr": {"timeout": 20}}}
