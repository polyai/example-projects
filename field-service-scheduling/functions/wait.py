from _gen import *  # <AUTO GENERATED>


@func_description("wait for the user response")
def wait(conv: Conversation):
    if conv.state.wait_counter is None:
        conv.state.wait_counter = 0

    conv.state.wait_counter += 1
    if conv.state.wait_counter % 3 == 0:
        return "Let the user know that you're still waiting for them."
    else:
        return {"utterance": ""}
