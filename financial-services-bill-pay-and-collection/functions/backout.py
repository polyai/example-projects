from _gen import *  # <AUTO GENERATED>


@func_description(
    "[Agent Behaviour] Call when you started the wrong task for the caller. It leaves the current task, so you can help with what they actually want."
)
def backout(conv: Conversation):
    conv.write_metric("BACKOUT")
    conv.exit_flow()
    return {"utterance": "Sorry about that! What can I help you with?"}
