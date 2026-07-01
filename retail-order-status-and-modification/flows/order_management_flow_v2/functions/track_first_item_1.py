from _gen import *  # <AUTO GENERATED>
from functions.flow_2d90b044.determine_order_status import determine_order_status


@func_description("Track the first item in the user's order")
def track_first_item_1(conv: Conversation, flow: Flow):
    conv.state.picked_order = next(order for order in conv.state.order_details.order_lines)
    conv.state.remaining_items = [
        order for order in conv.state.order_details.order_lines if order != conv.state.picked_order
    ]
    # conv.state.user_wants_all_items = "The user has already said they want to know the status of all the items in the order, after hearing about the current item."
    determine_order_status(conv, flow)
