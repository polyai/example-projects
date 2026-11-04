from _gen import *  # <AUTO GENERATED>
from flows.schedule_appointment.functions.update_visit_request import (
    LOOKUP_KEY,
    check_open,
    missing_detail,
    request_state,
    visit_request,
)
from functions import visits
from functions.handoff import handoff

NO_AVAILABILITY = (
    "I'm sorry, I can't see any openings in the next two weeks. Let me put you through to our "
    "scheduling team, who may be able to fit you in. One moment, please."
)


@func_description(
    "Look up the open arrival windows for a visit: the day the caller asked for and the days around it, or the earliest from tomorrow. Call it whenever they say or change when suits, or ask for a day outside the windows you already have."
)
@func_parameter(
    "preferred_date",
    "The day they asked for as YYYY-MM-DD, from the date guide; 'earliest' if they want the soonest or any day. Empty if they haven't said.",
)
@func_parameter(
    "day_said",
    "Their words for the day, with the part of the day if they said one, e.g. 'Thursday morning', 'next Wednesday afternoon', 'today', 'earliest'. Empty if they haven't said.",
)
@func_latency_control(
    delay_before_responses_start=1,
    silence_after_each_response=3,
    delay_responses=[("Let me just check what we've got.", 3), ("Nearly there.", 3)],
)
def find_visit_time(conv: Conversation, flow: Flow, preferred_date: str, day_said: str):
    refusal = check_open(conv)
    if refusal:
        return refusal
    req = visit_request(conv)
    missing = missing_detail(req)
    if missing:
        return f'First ask: "{missing}" Then call this again.\n\n{request_state(conv)}'

    avail = visits.lookup(
        conv, LOOKUP_KEY, str(preferred_date or ""), str(day_said or "")
    )
    if avail["problem"]:
        return f"{avail['problem']}\n\n{request_state(conv)}"
    if avail["mode"] == "none":
        return f"Ask when suits them, then call this again.\n\n{request_state(conv)}"
    if not avail["windows"]:
        conv.write_metric("NO_AVAILABILITY_FOUND")
        return handoff(conv, "NO_AVAILABILITY_FOUND", NO_AVAILABILITY, "CUSTOMER_CARE")
    conv.write_metric("SLOT_OFFERED")
    text = visits.availability_text(conv, avail, "make_new_appointment")
    return f"{text}\n\n{request_state(conv)}"
