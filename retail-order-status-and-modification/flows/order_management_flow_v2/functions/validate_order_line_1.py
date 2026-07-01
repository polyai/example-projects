from _gen import *  # <AUTO GENERATED>
from flows.order_management_flow_v2.functions.determine_order_status_1 import (
    determine_order_status_1,
)


@func_description("Check which product the user means")
@func_parameter("order_line_number", "The order line number ")
def validate_order_line_1(conv: Conversation, flow: Flow, order_line_number: str):
    # Make sure your Flow function either transitions to a step or exits the flow:
    if order_line_number not in [
        str(order.order_line_number) for order in conv.state.order_details.order_lines
    ]:
        return "The order with the given number can't be found. Please try again."

    conv.state.picked_order = next(
        order
        for order in conv.state.order_details.order_lines
        if str(order.order_line_number) == order_line_number
    )
    conv.state.remaining_items = [
        order for order in conv.state.order_details.order_lines if order != conv.state.picked_order
    ]

    determine_order_status_1(conv, flow)
    # flow.goto_step("Start step")
