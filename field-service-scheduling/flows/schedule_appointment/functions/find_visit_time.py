from _gen import *  # <AUTO GENERATED>
from flows.schedule_appointment.functions.update_visit_request import (
    check_open,
    offer_next,
    visit_request,
)
from functions import visits


@func_description(
    "Save when the caller would like the visit and get the arrival window to offer, or the next one after the window they turned down. Call it whenever they say or change when suits, or turn down the window you offered."
)
@func_parameter(
    "preferred_date",
    "A specific day they asked for, as YYYY-MM-DD (the first day of a range such as 'next week'). 'any' if they're flexible about the day ('any day this week', 'whenever', 'as soon as possible'): the tool then offers the earliest window. Empty if not said.",
)
@func_parameter("time_of_day", "'morning', 'afternoon' or 'any'.")
@func_parameter(
    "wants_different_time",
    "'true' only when the caller turned down the window you offered without saying what they want instead. Otherwise 'false'.",
)
@func_latency_control(
    delay_before_responses_start=1,
    silence_after_each_response=3,
    delay_responses=[("Let me see what we have.", 3), ("One more moment.", 3)],
)
def find_visit_time(
    conv: Conversation,
    flow: Flow,
    preferred_date: str,
    time_of_day: str,
    wants_different_time: str,
):
    refusal = check_open(conv)
    if refusal:
        return refusal

    req = visit_request(conv)
    before = (req["preferred_date"], req["time_of_day"])
    if str(preferred_date or "").strip():
        req["preferred_date"] = preferred_date.strip()
    part = str(time_of_day or "").strip().lower()
    if part in visits.TIME_OF_DAY:
        req["time_of_day"] = part
    rejected = str(wants_different_time).strip().lower() == "true"
    if rejected and not req["preferred_date"]:
        req["preferred_date"] = "any"
    changed = before != (req["preferred_date"], req["time_of_day"])
    return offer_next(conv, req, rejected=rejected, preference_changed=changed)
