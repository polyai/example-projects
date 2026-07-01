from _gen import *  # <AUTO GENERATED>


@func_description("Transition to step Schedule appointment")
def go_to_collect_additional_notes(conv: Conversation, flow: Flow):
    flow.goto_step("Schedule appointment")
    return """Say to the user: "Great! Are there any other concerns you'd like us to note before we lock that in?"
 """
