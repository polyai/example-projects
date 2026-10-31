from _gen import *  # <AUTO GENERATED>


@func_description(
    "You misunderstood what the caller wants, or they no longer want the task you're on: leave it and ask what they need."
)
def backout(conv: Conversation):
    conv.exit_flow()
    conv.write_metric("ESCAPED_PRIMARY_INTENT", None)
    conv.state.task = ""
    return 'Say: "Sorry about that! What can I do for you?"'
