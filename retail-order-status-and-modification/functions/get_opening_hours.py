from _gen import *  # <AUTO GENERATED>
from functions import sms
from functions.in_hours import in_hours
from functions.store_info import attr
from functions.utils import (
    DAYS,
    day_hours,
    hours_not_to_hand,
    next_opening,
    now_local,
    spoken_time,
    variant_opening_hours,
)


def _not_to_hand(conv, record: bool) -> str:
    """The line for hours we don't have, with the website offer when there's a website. The
    offer is recorded only when it's the answer (blank hours)."""
    say = hours_not_to_hand(conv)
    if attr(conv, "website_url"):
        say += " " + (
            sms.offer(conv, "website")
            if record
            else "Would you like me to text you the link?"
        )
    return say


@func_description(
    "Get this store's opening hours: today's, whether it's open now, and the week. Call it whenever the caller asks when the store is open."
)
def get_opening_hours(conv: Conversation):
    hours = variant_opening_hours(conv)
    unknown = _not_to_hand(conv, record=not hours)
    follow = (
        " A yes to the text offer → call start_send_sms with sms_id='website' and "
        "caller_agreed='true'."
        if attr(conv, "website_url")
        else ""
    )
    if not hours:
        return f"Say: \"{unknown}\" Don't guess or give any times, and never say we're closed.{follow}"
    now = now_local(conv)
    today = DAYS[now.weekday()]
    today_hours = day_hours(hours, today)
    if today_hours == "not listed":
        now_line = "We don't know today's hours."
    elif in_hours(conv):
        close = hours[today].split("-")[1]
        now_line = f"Open now, until {spoken_time(close, 'today')}."
    else:
        back = next_opening(conv, hours)
        now_line = f"Closed now; opens at {back}." if back else "Closed now."
    week = "; ".join(f"{d.capitalize()} {day_hours(hours, d)}" for d in DAYS)
    return (
        f"Today is {today.capitalize()}: {today_hours}. {now_line} The week, only if they ask "
        f"about another day or the whole week: {week}. Answer only what they asked, in a "
        "sentence, with times in words (\"We're open until 9 tonight.\"). For a day that's not "
        f'listed, say: "{unknown}" and never say we\'re closed that day.{follow}'
    )
