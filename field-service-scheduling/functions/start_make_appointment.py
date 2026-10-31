from _gen import *  # <AUTO GENERATED>
from functions import idnv


@func_description(
    "The caller wants a technician to come out: a new visit, a repair, a service call. Call it as soon as that's clear, even if they're also giving details."
)
def start_make_appointment(conv: Conversation):
    conv.write_metric("PRIMARY_INTENT", "MAKE_APPOINTMENT")
    conv.state.visit_request = None
    conv.state.booked_appointment_id = ""
    gate = idnv.require(conv, "schedule_appointment")
    if gate:
        return gate
    conv.goto_flow("schedule_appointment")
