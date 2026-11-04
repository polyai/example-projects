from _gen import *  # <AUTO GENERATED>


@func_description(
    'The caller needs a moment ("hang on", "let me find my bill"): after "Of course, take your time.", wait for them to speak.'
)
def wait(conv: Conversation):
    if conv.state.wait_counter is None:
        conv.state.wait_counter = 0

    conv.state.wait_counter += 1
    if conv.state.wait_counter % 3 == 1:
        return {"utterance": "Of course, take your time."}
    if conv.state.wait_counter % 3 == 0:
        return "Say: \"No rush, I'm still here whenever you're ready.\""
    else:
        return {"utterance": ""}
