from _gen import *  # <AUTO GENERATED>


@func_description("Caller wants to make a payment on their account (bill pay).")
def start_payments_flow(conv: Conversation):
    conv.goto_flow("payments general")
