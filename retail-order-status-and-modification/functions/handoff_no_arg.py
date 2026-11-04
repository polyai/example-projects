from _gen import *  # <AUTO GENERATED>


@func_description("System function for response control try handoff")
def handoff_no_arg(conv: Conversation):
    return {
        "content": (
            "ACTION - Immediately transfer the user by calling the 'handoff' function with the "
            "most appropriate handoff_reason based on the conversation history and the "
            "instructions in CONTEXT_INFORMATION, and handoff_utterance=\"I'll put you through to "
            'the team now. One moment, please."'
        )
    }
