from _gen import *  # <AUTO GENERATED>
from functions import billing


def balance_text(acct: dict) -> str:
    text = (
        f"Their balance is {billing.say_money(acct['balance'])}, due on "
        f"{billing.say_date(acct['due_date'])}."
    )
    scheduled = acct.get("scheduled_payments") or []
    if scheduled:
        items = "; ".join(
            f"{billing.say_money(p['amount'])} on {billing.say_date(p['date'])}"
            for p in scheduled
        )
        text += f" Payments already scheduled: {items}."
    return text


def check_balance(conv: Conversation, flow: Flow):
    """Entry gate: unverified callers go to verify_caller and come back here."""
    gate = billing.gate(conv, "account_balance")
    if gate:
        return gate

    acct = billing.verified_account(conv)
    conv.write_metric("BALANCE_GIVEN")
    flow.goto_step("Account Balance", "balance read")
    return (
        f"Tell the caller: {balance_text(acct)} Then ask if there's anything else.\n\n"
        + billing.call_state(
            conv, ["Task: balance", balance_text(acct)], "Ask if there's anything else."
        )
    )
