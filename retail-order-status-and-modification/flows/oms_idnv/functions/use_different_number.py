from _gen import *  # <AUTO GENERATED>
from functions.utterances import utterance


@func_description("Transition to phone number collecction.")
def use_different_number(conv: Conversation, flow: Flow):
    conv.write_metric("IDNV_PHONE_NUMBER_ALTERNATIVE")
    conv.say(utterance(conv, "idnv_use_different_number"))
    flow.goto_step("Collect phone number")
