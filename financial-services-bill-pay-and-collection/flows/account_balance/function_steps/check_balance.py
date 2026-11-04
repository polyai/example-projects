from _gen import *  # <AUTO GENERATED>
from functions import billing


def check_balance(conv: Conversation, flow: Flow):
    """Entry gate: unverified callers go to verify_caller and come back here."""
    gate = billing.gate(conv, "account_balance")
    if gate:
        return gate

    acct = billing.verified_account(conv)
    flow.goto_step("Account Balance", "balance read")
    state = billing.call_state(
        conv,
        ["Task: balance", billing.balance_sentence(conv, acct)],
        "Answer follow-ups; a payment goes through start_make_payment.",
    )
    if (
        conv.state.entry_said_turn is not None
        and conv.state.entry_said_turn == billing.history_turn(conv)
    ):
        # The tool that brought the caller here has already given the balance.
        return f"Follow the previous tool response.\n\n{state}"
    conv.write_metric("BALANCE_GIVEN")
    return f"{billing.balance_instruction(conv, acct)}\n\n{state}"
