from _gen import *  # <AUTO GENERATED>
from functions import visits

ASK_CHANGE = "Is there anything you'd like to change?"


def check_line(conv, visit: dict) -> str:
    """The check-a-visit readback: one sentence, then the question."""
    return f"You've got {visits.describe_visit(visit, conv)}. {ASK_CHANGE}"


@func_description(
    "The caller has several upcoming visits and has said which one they mean. Pass its date."
)
@func_parameter("visit_date", "The date of the visit they mean, as YYYY-MM-DD.")
@func_parameter("time_of_day", "'morning' or 'afternoon' if they said, else 'any'.")
def choose_visit(conv: Conversation, visit_date: str, time_of_day: str):
    visit = visits.choose_visit_by_date(conv, visit_date, time_of_day)
    if not visit:
        listing = "; ".join(
            visits.visit_label(a, conv) for a in visits.upcoming_visits(conv)
        )
        return (
            f"NOT CHOSEN: that doesn't pick out one visit. Their visits: {listing}. Ask which one "
            "they mean. Then call choose_visit again with whatever they say, even if it's the same "
            "as before."
        )
    task = conv.state.task
    if task == "cancel":
        from flows.cancel_appointment.functions.cancel_visit import cancel_readback

        return cancel_readback(conv)
    if task == "reschedule":
        said = visits.describe_visit(visit, conv)
        return (
            f"They mean {said}. If they've said when they'd like it instead, call find_new_time "
            "with it now ('sooner', 'earlier' or 'as soon as possible' is preferred_date="
            "'earliest'). Otherwise ask: \"What day would work better for you?\""
        )
    return f'Say: "{check_line(conv, visit)}"'
