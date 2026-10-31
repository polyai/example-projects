from _gen import *  # <AUTO GENERATED>
from functions import idnv


@func_description(
    "The caller wants to check or confirm an upcoming visit: when it is, whether someone is coming."
)
def start_confirm_appointment(conv: Conversation):
    conv.write_metric("PRIMARY_INTENT", "CONFIRM_APPOINTMENT")
    gate = idnv.require(conv, "confirm_appointment")
    if gate:
        return gate
    conv.goto_flow("confirm_appointment")
