from _gen import *  # <AUTO GENERATED>
from functions import bookings, hours

BLANK = "I'm sorry, I don't have our opening hours in front of me."


@func_description(
    "Get the opening hours for one day, or the week, and whether we're open right now. Call it whenever the caller asks when we're open or closed, or whether we're open now."
)
@func_parameter(
    "date",
    "The day they asked about as YYYY-MM-DD (use the date guide). Empty for today. 'week' only if they asked for the whole week.",
)
@func_parameter(
    "day_said",
    "The caller's own words for the day, e.g. 'Sunday', 'tonight'. Empty if they didn't say one.",
)
def get_opening_hours(conv: Conversation, date: str, day_said: str):
    if not hours.known(conv):
        return (
            f'Say: "{BLANK}" Never say whether we\'re open or closed, and never give a time. Offer '
            'to put them through to the team ("I can put you through to the team, though. Would '
            'that help?"), unless you were in the middle of something: then carry on with it. '
            "Offer the team once: if they say no, say that's fine and ask if there's anything else. "
            "Never offer again, and never put them through without a yes."
        )
    right_now = hours.say_open_now(conv, bookings.now(conv))
    if str(date or "").strip().lower() == "week":
        return (
            f"Our hours: {hours.summary(conv)} Give the caller what they asked for, briefly, then "
            "carry on with anything you were in the middle of."
        )
    day, problem = bookings.resolve_day(conv, date, day_said)
    if problem:
        return problem
    day = day or bookings.today(conv)
    shifts = hours.shifts_on(conv, day) or []
    name = bookings.day_name(conv, day.isoformat())
    if not shifts:
        line = f"We're closed {'today' if name == 'today' else 'on ' + day.strftime('%A') + 's'}."
    else:
        close = hours.say_shifts(shifts[-1:]).split(" to ")[-1]
        tonight = "tonight" if name == "today" else f"on {day.strftime('%A')}"
        line = f"We're open {hours.say_shifts(shifts)} {tonight}" + "."
        if name == "today":
            line = f"We're open until {close} tonight."
    return (
        f'Answer only what they asked, in a sentence: "{line}" If they asked whether we\'re open '
        f'right now, say exactly this instead: "{right_now}" Never work it out yourself. Then carry '
        "on with anything you were in the middle of."
    )
