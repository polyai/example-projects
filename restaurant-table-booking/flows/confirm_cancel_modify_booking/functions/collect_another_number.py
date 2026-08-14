from _gen import *  # <AUTO GENERATED>


@func_description(
    "Call this if you need to collect another phone number, or if the user wants to end the call"
)
@func_parameter(
    "should_collect_another_number", "Should we try and collect another number"
)
def collect_another_number(
    conv: Conversation, flow: Flow, should_collect_another_number: bool
):
    if should_collect_another_number:
        flow.goto_step("Collect phone number")
        return "Try to collect another number"
    else:
        conv.exit_flow()
        return "Ask the user if there is anything else you can help with"
