from _gen import *  # <AUTO GENERATED>


@func_description(
    "Call this function as soon as the user mentions something else they need help with, for example, if they want to track another item"
)
@func_parameter(
    "next_item", "(Optional) The product that the user just mentioned, if they mentioned one."
)
def track_next_order_1(conv: Conversation, flow: Flow, next_item: str):
    conv.state.next_item = next_item
    if conv.state.multiple_items_same_description:
        flow.goto_step("Decide which item entry to look at")
    else:
        flow.goto_step("track next item")
