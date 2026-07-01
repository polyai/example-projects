from _gen import *  # <AUTO GENERATED>


@func_description(
    "Go back to choosing which booking. Use when the user wants a different booking (e.g. 'the other one', 'the one on the 22nd')."
)
def go_to_determine_booking(conv: Conversation, flow: Flow):
    flow.goto_step("Determine booking")
