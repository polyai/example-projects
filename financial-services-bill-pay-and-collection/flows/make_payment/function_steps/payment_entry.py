from _gen import *  # <AUTO GENERATED>
from flows.make_payment.functions.update_payment import fresh_payment, payment_state
from functions import billing


def payment_entry(conv: Conversation, flow: Flow):
    """Entry gate: unverified callers go to verify_caller and come back here."""
    gate = billing.gate(conv, "make_payment")
    if gate:
        return gate

    conv.write_metric("PAYMENT_FLOW_INITIATED", write_once=True)
    if not isinstance(conv.state.payment, dict) or conv.state.payment.get("paid"):
        conv.state.payment = fresh_payment(conv)
    flow.goto_step("Make Payment", "caller verified")
    acct = billing.verified_account(conv)
    return (
        f"Help the caller make a payment. Their balance is {billing.say_money(acct['balance'])}, "
        f"due on {billing.say_date(acct['due_date'])}. If they have already said how much, call "
        "update_payment with it now; otherwise tell them the balance and ask how much they'd "
        f"like to pay.\n\n{payment_state(conv)}"
    )
