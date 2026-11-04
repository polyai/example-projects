from _gen import *  # <AUTO GENERATED>

LINE = "Of course, take your time."


@func_description(
    "The caller needs a moment ('hang on', 'let me check my diary'): say you'll wait, and wait until they speak again."
)
def wait(conv: Conversation):
    if conv.state.wait_counter is None:
        conv.state.wait_counter = 0

    conv.state.wait_counter += 1
    # The caller hesitated: whatever they say next, the write asks its question again first.
    conv.state.hesitated = True
    if conv.state.wait_counter % 3 == 0:
        return (
            "Let the caller know, briefly, that you're still here when they're ready."
        )
    return {"utterance": LINE}
