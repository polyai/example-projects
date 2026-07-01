from _gen import *  # <AUTO GENERATED>


@func_description("Call this function when the user has provided an order number")
@func_parameter("order_number", "The order number provided.")
def order_number_collected(conv: Conversation, flow: Flow, order_number: str):
    number = order_number.replace("-", "")
    number = number.replace(" ", "")
    number = number.replace(".", "")

    if number.startswith("P") or number.startswith("U") or len(number) > 10:
        flow.goto_step("Collect full order number")
        return flow.functions.full_order_number_provided(full_order_number=order_number)
    else:
        return flow.functions.phone_number_provided(conv, flow, order_number)
