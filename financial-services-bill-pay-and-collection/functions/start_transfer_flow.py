from _gen import *  # <AUTO GENERATED>


@func_description("Caller wants to transfer money to another account.")
def start_transfer_flow(conv: Conversation):
    conv.goto_flow("transfer_money")
