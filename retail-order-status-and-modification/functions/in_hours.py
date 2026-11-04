from datetime import time

from _gen import *  # <AUTO GENERATED>
from functions.utils import DAYS, now_local, variant_opening_hours


@func_description(
    "[UTIL] Whether the store is open now, from the variant's opening hours"
)
def in_hours(conv: Conversation) -> bool:
    """True when the variant's opening_hours say the store is open right now.

    Hours and timezone come from the variant (opening_hours, timezone), so the per-site values
    onboarding writes are the ones used. Blank or unreadable hours count as open, and so does a
    day missing from a filled-in list: it's unknown, never closed. Onboarding leaves the hours
    blank when it can't check them, and the only thing this gates is whether a caller can be put
    through, so a guessed schedule would turn away callers the team could take.
    settings.force_ooh_enabled in real-time config forces closed for testing.
    """
    if ((conv.real_time_config or {}).get("settings") or {}).get(
        "force_ooh_enabled", False
    ):
        conv.log.info("Force OOH enabled")
        return False

    hours = variant_opening_hours(conv)
    if not hours:
        conv.log.warning("No readable opening_hours on the variant, treating as open")
        return True

    now = now_local(conv)
    span = hours.get(DAYS[now.weekday()])
    if span is None:
        return True  # not listed: unknown, so open
    if span == "closed":
        return False
    start, end = span.split("-")
    open_at = time(*map(int, start.split(":")))
    close_at = time(*map(int, end.split(":")))
    return open_at <= now.time() < close_at
