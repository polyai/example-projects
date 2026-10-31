from _gen import *  # <AUTO GENERATED>
from functions import idnv


@func_description(
    "The caller wants to move an existing appointment to another day or time. Call it as soon as that's clear, including when they change their mind part-way through another task."
)
def start_rescheduling_flow(conv: Conversation):
    conv.write_metric("PRIMARY_INTENT", "RESCHEDULE_APPOINTMENT")
    conv.state.move_request = None
    gate = idnv.require(conv, "reschedule_appointment", strength=idnv.STRICT)
    if gate:
        return gate
    conv.goto_flow("reschedule_appointment")
