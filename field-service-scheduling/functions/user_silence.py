from _gen import *  # <AUTO GENERATED>


@func_description("Call this function if the user is silent")
def user_silence(conv: Conversation):
    if not conv.state.silence_counter:
        # if we set to 0, then `not conv.state.silence_counter` would be True
        conv.state.silence_counter = 1
        return {"utterance": "How can I help you today?"}

    conv.state.silence_counter += 1

    if conv.state.silence_counter == 2:
        return {"utterance": "How can I assist you?"}
    # conv.state.silence_counter == 3
    else:
        return {
            "hangup": True,
            "utterance": "Sorry, but I still can't hear you. Feel free to call back anytime! Goodbye.",
        }
