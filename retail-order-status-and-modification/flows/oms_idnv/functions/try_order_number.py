from _gen import *  # <AUTO GENERATED>


@func_description("Call only when the user want to try using order number.")
def try_order_number(conv: Conversation, flow: Flow):
    flow.goto_step("Collect full order number")
    return "Acknowledge the user (e.g. 'Sure...') if the user explicitly asks to provide the order number."
