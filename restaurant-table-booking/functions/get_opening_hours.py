from _gen import *  # <AUTO GENERATED>
from functions import bookings, hours


@func_description(
    "Get the opening hours, for the week or for one day, and whether we're open right now. Call it whenever the caller asks when we're open or closed, or whether we're open now."
)
@func_parameter(
    "date",
    "A specific date they asked about as YYYY-MM-DD (use the date guide). Empty for the week.",
)
def get_opening_hours(conv: Conversation, date: str):
    if not hours.known(conv):
        return (
            "You don't have the opening hours to hand. Say so briefly, and don't say whether we're "
            "open or closed right now. Then carry on with anything you were in the middle of."
        )
    right_now = (
        f" Right now: {hours.say_open_now(conv, bookings.now(conv))} If they asked whether we're "
        "open now, say exactly that; never work it out yourself."
    )
    day = bookings.parse_date(conv, date)
    if day:
        return (
            f"Tell the caller: {hours.say_day(conv, day)}. If they only asked about opening or "
            f"closing, give just that.{right_now} Then carry on with anything you were in the "
            "middle of."
        )
    return (
        f"Our hours: {hours.summary(conv)}{right_now} Give the caller what they asked about, "
        "briefly, then carry on with anything you were in the middle of."
    )
