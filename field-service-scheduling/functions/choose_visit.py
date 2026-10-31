from _gen import *  # <AUTO GENERATED>
from functions import visits


@func_description(
    "The caller has several upcoming visits and has said which one they mean. Pass its date."
)
@func_parameter("visit_date", "The date of the visit they mean, as YYYY-MM-DD.")
@func_parameter("time_of_day", "'morning' or 'afternoon' if they said, else 'any'.")
def choose_visit(conv: Conversation, visit_date: str, time_of_day: str):
    visit = visits.choose_visit_by_date(conv, visit_date, time_of_day)
    if not visit:
        listing = "; ".join(
            visits.describe_visit(a, conv) for a in visits.upcoming_visits(conv)
        )
        return (
            f"NOT CHOSEN: that doesn't pick out one visit. Their visits: {listing}. Ask which one "
            "they mean. Then call choose_visit again with whatever they say, even if it's the same "
            "as before."
        )
    task = conv.state.task
    described = visits.describe_visit(visit, conv)
    if task == "cancel":
        from flows.cancel_appointment.functions.cancel_visit import cancel_readback

        return cancel_readback(conv)
    if task == "reschedule":
        return f"They mean {described}. Ask when would suit them instead, unless they've said."
    return f"Read the visit back in one natural sentence: {described}. Ask if that sounds right."
