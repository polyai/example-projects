from _gen import *  # <AUTO GENERATED>


@func_description(
    "Call this function when the user has said something that suggests they don't need any more help tracking their order."
)
def help_with_next_issue(conv: Conversation, flow: Flow):
    # Make sure your Flow function either transitions to a step or exits the flow
    flow.goto_step("anything else")
