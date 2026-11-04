from _gen import *  # <AUTO GENERATED>
from functions import appointments


@func_description(
    "The caller wants to check an upcoming appointment: when it is, or who it's with."
)
def start_confirmation_flow(conv: Conversation):
    conv.write_metric("PRIMARY_INTENT", "CONFIRM_APPOINTMENT")
    gate = appointments.gate(conv, "confirm_appointment")
    if gate:
        return gate
    conv.goto_flow("confirm_appointment")
    return "CHECK: the caller is verified. Carry on with their appointment."
