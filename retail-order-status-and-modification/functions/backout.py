from _gen import *  # <AUTO GENERATED>


@func_description(
    "You misunderstood the user's original intent and now need to back out of the flow you're in."
)
def backout(conv: Conversation):
    conv.exit_flow()
    return """Say: "Sorry, I must have misunderstood. What can I do for you today?"""
