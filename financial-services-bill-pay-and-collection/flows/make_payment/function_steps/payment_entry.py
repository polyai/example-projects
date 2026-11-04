from _gen import *  # <AUTO GENERATED>
from functions import billing, payments


def payment_entry(conv: Conversation, flow: Flow):
    """Entry gate: unverified callers go to verify_caller and come back here."""
    gate = billing.gate(conv, "make_payment")
    if gate:
        return gate

    conv.write_metric("PAYMENT_FLOW_INITIATED", write_once=True)
    flow.goto_step("Make Payment", "caller verified")
    if (
        conv.state.entry_said_turn is not None
        and conv.state.entry_said_turn == billing.history_turn(conv)
    ):
        # The tool that brought the caller here has already said what comes next.
        return f"Follow the previous tool response.\n\n{payments.state_block(conv)}"
    return f"{payments.entry_instruction(conv)}\n\n{payments.state_block(conv)}"
