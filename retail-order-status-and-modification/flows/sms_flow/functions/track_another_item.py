from _gen import *  # <AUTO GENERATED>


@func_description("Track another item in the user's order")
@func_parameter(
    "next_item",
    "(Optional) The product that the user just mentioned, if they mentioned one.",
)
def track_another_item(conv: Conversation, flow: Flow, next_item: str):
    print(conv.state.order_items_listing)
    conv.state.next_item = next_item
    if conv.state.idnv_passed:
        return {
            "transition": {"goto_flow": "OMS_WISMO", "goto_step": "Track another item"}
        }
