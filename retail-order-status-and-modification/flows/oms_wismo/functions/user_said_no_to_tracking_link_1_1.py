from _gen import *  # <AUTO GENERATED>
from functions.utterances import utterance


@func_description("Transition to step deny tracking link")
def user_said_no_to_tracking_link_1_1(conv: Conversation, flow: Flow):
    flow.goto_step("Determine what user needs next")
    return {"utterance": utterance(conv, "anything_else")}
