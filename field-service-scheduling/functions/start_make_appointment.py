from _gen import *  # <AUTO GENERATED>
from functions import idnv

URGENT_FIRST = (
    "Before anything else: if the problem is urgent (water pouring or flooding, no heat, no AC, a "
    "gas leak that's been made safe, or they say it's an emergency or can't wait) and you "
    "haven't made the urgent offer yet, make it now instead of asking for their account (after a "
    "gas leak that's been dealt with, start with \"Oh, I'm glad you're safe.\"). Otherwise:"
)


@func_description(
    "The caller wants a technician to come out: a new visit, a repair, a service call. Call it as soon as that's clear, even if they're also giving details. Not for an 'okay' to something you told them: ask whether they'd like a visit first."
)
@func_parameter(
    "day_said",
    "Their words for when, if they've already said it (e.g. 'today', 'Thursday morning', 'earliest'). Empty string otherwise.",
)
def start_make_appointment(conv: Conversation, day_said: str):
    conv.write_metric("PRIMARY_INTENT", "MAKE_APPOINTMENT")
    conv.state.visit_request = None
    conv.state.day_said = str(day_said or "").strip()
    conv.state.booked_appointment_id = ""
    gate = idnv.require(conv, "schedule_appointment")
    if gate:
        return f"{URGENT_FIRST} {gate}"
    conv.goto_flow("schedule_appointment")
