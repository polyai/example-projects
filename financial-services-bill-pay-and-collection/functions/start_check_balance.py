from _gen import *  # <AUTO GENERATED>
from functions import billing


@func_description(
    "The caller wants to know their balance or how much they owe. Call it as soon as that's clear, even if they're also giving details."
)
def start_check_balance(conv: Conversation):
    conv.write_metric("PRIMARY_INTENT", "CHECK_BALANCE")
    gate = billing.gate(conv, "account_balance")
    if gate:
        return gate
    conv.goto_flow("account_balance")
