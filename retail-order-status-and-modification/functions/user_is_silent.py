import re

from _gen import *  # <AUTO GENERATED>
from functions.transfer_call import transfer_call

from .create_call_summary import CREATE_CALL_SUMMARY_PROMPT
from .utterances import utterance


@func_description("Call only when the user were silent in previous turn.")
def user_is_silent(conv: Conversation):
    # Count the number of silence turn
    silence_turn_count = 0
    last_agent_utterance = ""
    reversed_conv_history = list(reversed(conv.history))
    for i, turn in enumerate(reversed_conv_history):
        if turn.role == "user":
            if turn.text == "":
                last_agent_utterance = reversed_conv_history[i + 1].text
                silence_turn_count += 1
            else:
                break

    # Extract the question from the utterance
    match = re.search(r"[^.!?]*\?+", last_agent_utterance)
    # question = match.group(0).strip() if match else last_agent_utterance

    if silence_turn_count == 0:
        return "Repeat your last question/request but make it more shorter."
    if silence_turn_count <= 2:
        if match:
            return f"Repeat your last question/request - '{match.group(0).strip()}' - but rephrase it for variety shorter."
        else:
            return " Say: 'Is there anything else I can do for you today?' Rephrase for variety."
    elif silence_turn_count == 3:
        return {"utterance": utterance(conv, "still_on_line")}
    # silence_turn_count > 3
    elif conv.state.transfer_on_silence_loop:
        return transfer_call(
            conv,
            "DEFAULT",
            "EMPTY_INPUT_LOOP",
            utterance(conv, "silence_loop_transfer"),
        )
    else:
        # Equivalent to end_call() function but with diffenrent utterance
        conv.state.call_outcome = "hangup"
        conv.state.action_after_call_summary = {
            "utterance": utterance(conv, "silence_callback"),
            "hangup": True,
        }
        return {"content": CREATE_CALL_SUMMARY_PROMPT}
