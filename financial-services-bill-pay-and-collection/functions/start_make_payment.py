from _gen import *  # <AUTO GENERATED>
from functions import billing, payments


@func_description(
    "The caller wants to make a payment on their account or pay their bill, or says yes to making one. Call it as soon as that's clear, even if they're also giving details."
)
def start_make_payment(conv: Conversation):
    conv.write_metric("PRIMARY_INTENT", "MAKE_PAYMENT")
    payment = conv.state.payment
    if isinstance(payment, dict) and payment.get("paid"):
        conv.state.payment = None  # a second payment on the same call starts fresh
    gate = billing.gate(conv, "make_payment")
    if gate:
        return gate
    line = payments.entry_instruction(conv)
    conv.state.entry_said_turn = billing.history_turn(conv)
    conv.goto_flow("make_payment")
    return line
