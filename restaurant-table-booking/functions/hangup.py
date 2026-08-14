import time

from _gen import *  # <AUTO GENERATED>


@func_description(
    "End the conversation by hanging up on the user - do not use if transferring"
)
def hangup(conv: Conversation):
    time.sleep(3)
    return {"hangup": True}
