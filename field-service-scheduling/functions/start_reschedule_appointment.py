from _gen import *  # <AUTO GENERATED>
from functions import idnv


@func_description(
    "The caller wants to move an existing visit to another day or time, including changing their mind mid-booking and asking to move a visit they already have instead."
)
def start_reschedule_appointment(conv: Conversation):
    conv.write_metric("PRIMARY_INTENT", "MODIFY_APPOINTMENT")
    conv.state.move_request = None
    gate = idnv.require(conv, "reschedule_appointment")
    if gate:
        return gate
    conv.goto_flow("reschedule_appointment")
