from _gen import *  # <AUTO GENERATED>


@func_description("Try and collect the user's full order number instead.")
def try_collect_order_number(conv: Conversation):
    flow.goto_step("Collect full order number")
