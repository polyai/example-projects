from _gen import *  # <AUTO GENERATED>
from functions.transfer_call import transfer_call

from .create_call_summary import CREATE_CALL_SUMMARY_PROMPT
from .utterances import utterance


@func_description(
    "Play a goodbye message and end the conversation. Do this if and only if the user stay silent for multiple turns."
)
def handle_silence_loop(conv: Conversation):
    if conv.state.transfer_on_silence_loop:
        return transfer_call(
            conv,
            "DEFAULT",
            "EMPTY_INPUT_LOOP",
            utterance(conv, "silence_loop_transfer"),
        )

    conv.state.call_outcome = "hangup"
    conv.state.action_after_call_summary = {
        "utterance": utterance(conv, "silence_loop_hangup"),
        "hangup": True,
    }
    return {"content": CREATE_CALL_SUMMARY_PROMPT}
