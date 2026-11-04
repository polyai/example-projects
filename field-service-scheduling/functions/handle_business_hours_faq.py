from datetime import timedelta

from _gen import *  # <AUTO GENERATED>
from functions.in_hours import in_hours
from functions.utils import (
    DAYS,
    HOURS_NOT_TO_HAND,
    day_hours_sentence,
    hours_on,
    next_opening,
    site_hours_utterance,
    site_now,
    site_opening_hours,
)


def _clock_close(conv) -> str:
    span = hours_on(site_opening_hours(conv), site_now(conv).date())
    if not span:
        return ""
    h, m = map(int, span[1].split(":"))
    h12 = h % 12 or 12
    said = f"{h12}:{m:02d}" if m else f"{h12}"
    return f"{said} tonight" if h >= 17 else f"{said} today"


@func_description(
    "The caller asks about the office's opening hours, or whether we're open now. Office hours aren't visit windows: 'when can a technician come?' is a booking."
)
@func_parameter(
    "day_asked",
    "The day they asked about: 'today', 'tomorrow' or a weekday name; 'now' if they asked whether we're open now; 'week' only if they asked for the whole week. 'today' if they didn't say.",
)
def handle_business_hours_faq(conv: Conversation, day_asked: str):
    hours = site_opening_hours(conv)
    if not site_hours_utterance(conv):
        return (
            f'Say: "{HOURS_NOT_TO_HAND} I can put you through to the team, though. Would that '
            "help?\" Never say we're closed, and don't give or guess any times. Booking works as "
            "normal. Then carry on with anything you were in the middle of."
        )
    asked = str(day_asked or "today").strip().lower()
    now = site_now(conv)
    if asked == "week":
        return (
            f"Tell the caller: {site_hours_utterance(conv)} Then carry on with anything you were "
            "in the middle of."
        )
    if asked == "now":
        if in_hours(conv):
            line = f"Yes, we're open now, until {_clock_close(conv)}."
        else:
            opening = next_opening(conv)
            line = "No, we're closed right now." + (
                f" We're open again {opening}." if opening else ""
            )
        return f'Say exactly: "{line}" Then carry on with anything you were in the middle of.'
    day = now.date()
    if asked == "tomorrow":
        day += timedelta(days=1)
    elif asked in DAYS:
        day += timedelta(days=(DAYS.index(asked) - day.weekday()) % 7)
    span = hours_on(hours, day)
    fact = day_hours_sentence(conv, day)
    if day == now.date() and span:
        fact += f" We close at {_clock_close(conv)}."
    return (
        f"The hours they asked about: {fact} Answer only what they asked, in one short sentence "
        '("We\'re open until 7 tonight."). Give the whole week only if they ask for it. Then '
        "carry on with anything you were in the middle of."
    )
