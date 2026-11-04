from _gen import *  # <AUTO GENERATED>
from functions import billing


@func_description(
    "The caller wants to know their balance, how much they owe or when it's due. Call it as soon as that's clear, even if they're also giving details. Not for a bank balance."
)
def start_check_balance(conv: Conversation):
    conv.write_metric("PRIMARY_INTENT", "CHECK_BALANCE")
    gate = billing.gate(conv, "account_balance")
    if gate:
        return gate
    acct = billing.verified_account(conv)
    conv.write_metric("BALANCE_GIVEN")
    line = billing.balance_instruction(conv, acct)
    conv.state.entry_said_turn = billing.history_turn(conv)
    conv.goto_flow("account_balance")
    return line
