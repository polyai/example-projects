from _gen import *  # <AUTO GENERATED>
from functions import idnv


@func_description(
    "The caller wants to check or confirm an upcoming appointment: when it is, or who it's with."
)
def start_confirmation_flow(conv: Conversation):
    conv.write_metric("PRIMARY_INTENT", "CONFIRM_APPOINTMENT")
    gate = idnv.require(conv, "confirm_appointment", strength=idnv.STRICT)
    if gate:
        return gate
    conv.goto_flow("confirm_appointment")
