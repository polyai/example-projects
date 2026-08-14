import random

from _gen import *  # <AUTO GENERATED>

from .utterances import utterance, utterance_list


def user_spoke_since_last_silence(conv: Conversation):
    saw_previous_silence = False

    # Logic to reset silence counter so user can have multiple instances of silence in one conv
    for event in reversed(conv.history):
        if event.role != "user":
            continue
        if not event.text:
            if saw_previous_silence:
                # Two silent turns with nothing in between
                break
            saw_previous_silence = True
        elif saw_previous_silence:
            # Found speech after last silence -> reset needed
            return True
    return False


@func_description(
    "Handles the user's request to wait or if the user is silent. This function should be called as many times as needed."
)
@func_parameter(
    "user_requested_wait",
    "Whether the user has requested time or not in a previous turn. Check up to the last THREE user turns to make sure this value is correct; if the user has asked you to wait in one of the last three turns, this value will be TRUE. Defaults to TRUE.",
)
@func_parameter("times_called", "Number of times this function has been called")
def handle_wait_and_silence(
    conv: Conversation, user_requested_wait: bool, times_called: int
):
    # Determine if user was silent this turn
    user_silent = True  # Defaults to silent if no user event found
    for event in reversed(conv.history):
        if event.role == "user":
            user_silent = not bool(event.text)
            break

    # Handle VALID wait request (user asked and actually spoke)
    if user_requested_wait and not user_silent:
        conv.state.user_requested_wait = True  # affirm wait mode
        conv.state.wait_turns = 0  # reset wait patience
        conv.state.silence_counter = 0  # reset silence tracking
        return {
            "utterance": utterance(conv, "wait_acknowledge"),
            "listen": {"asr": {"timeout": 15}},
        }

    # User spoke but didn't request wait (reset and prompt LLM)
    if not user_silent:
        if conv.state.user_requested_wait:
            conv.state.user_requested_wait = False
        conv.state.wait_turns = 0
        conv.state.silence_counter = 0
        return {
            "content": "The user has spoken, so wait and silence handling isn't needed. You can respond directly, or ask how you can help."
        }

    # User is silent
    if conv.state.user_requested_wait:
        # In wait mode, track wait turns
        conv.state.wait_turns = (
            conv.state.wait_turns + 1 if conv.state.wait_turns else 1
        )
        # User exceeds wait period
        if conv.state.wait_turns >= 2:
            conv.state.user_requested_wait = False  # Exit wait mode
            conv.state.wait_turns = 0
            conv.state.silence_counter = 1
            return {"utterance": utterance(conv, "still_there")}
        else:
            return {
                "utterance": random.choice(utterance_list(conv, "wait_patience")),
                "listen": {"asr": {"timeout": 15}},
            }

    # Silence behavior when not in wait mode
    if user_spoke_since_last_silence(conv):
        conv.state.silence_counter = 1
    else:
        conv.state.silence_counter = (
            conv.state.silence_counter + 1 if conv.state.silence_counter else 1
        )

    # Determine utterance based on silence iteration
    if conv.state.silence_counter == 1:
        return "Repeat your last question/request but make it a bit shorter."
    elif conv.state.silence_counter == 2:
        return {"utterance": utterance(conv, "still_there_help")}
    else:
        return {
            "hangup": True,
            "utterance": utterance(conv, "silence_goodbye"),
        }
