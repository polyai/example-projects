from _gen import *  # <AUTO GENERATED>


@func_description(
    "you misunderstood the user's original intent and now need to apologise and back out of the collection flow that you are in"
)
def backout(conv: Conversation):
    conv.exit_flow()
    conv.write_metric("ESCAPED_PRIMARY_INTENT", None)
    return """Say: "Sorry! What can I do for you today?"
  """
