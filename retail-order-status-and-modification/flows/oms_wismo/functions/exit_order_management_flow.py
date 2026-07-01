from _gen import *  # <AUTO GENERATED>


@func_description("Exit the order management flow")
def exit_order_management_flow(conv: Conversation, flow: Flow):
    conv.exit_flow()
