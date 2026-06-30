from _gen import *  # <AUTO GENERATED>


@func_description(
    "Called when the user says no or doesn't know if their calling number is on file."
)
def go_to_collect_phone(conv: Conversation, flow: Flow):
    flow.goto_step("Collect Phone Number")
    return {}
