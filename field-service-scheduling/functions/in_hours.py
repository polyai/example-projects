from _gen import *  # <AUTO GENERATED>
import re
from datetime import datetime, time

from functions.utils import DAYS, site_opening_hours, site_timezone

_READABLE = re.compile(r"^(closed?|\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2})$", re.IGNORECASE)


@func_description("check if the call is within business hours")
def in_hours(conv: Conversation):
    """Whether the site is open now, from the `opening_hours` and `timezone` variant
    attributes. The force_ooh_enabled switch stays in real-time config.

    Blank or unreadable hours count as open: onboarding leaves `opening_hours` blank when
    it can't check them, and many field service lines take calls around the clock, so a
    caller is never shut out on hours nobody has set."""
    settings = (conv.real_time_config or {}).get("settings", {})
    if settings.get("force_ooh_enabled", False):
        conv.log.info("Force OOH enabled")
        return False

    opening_hours = site_opening_hours(conv)
    if not any(_READABLE.match(v.strip()) for v in opening_hours.values()):
        conv.log.warning(
            "opening_hours variant attribute is blank or unreadable, treating as open"
        )
        return True

    timezone_name, timezone = site_timezone(conv)
    now = conv.state.datetime_now.astimezone(timezone)
    today = now.date().isoformat()
    hours_str = opening_hours.get(today) or opening_hours.get(
        DAYS[now.weekday()], "closed"
    )
    conv.log.info(
        "Hours for today", date=today, hours=hours_str, timezone=timezone_name
    )

    if hours_str.strip().lower() in ("closed", "close"):
        return False

    try:
        start_str, end_str = hours_str.split("-")
        start_hour, start_minute = map(int, start_str.strip().split(":"))
        end_hour, end_minute = map(int, end_str.strip().split(":"))
        start = datetime.combine(
            now.date(), time(start_hour, start_minute), tzinfo=timezone
        )
        if (end_hour, end_minute) in ((0, 0), (24, 0)):
            end = datetime.combine(now.date(), time(23, 59, 59), tzinfo=timezone)
        else:
            end = datetime.combine(
                now.date(), time(end_hour, end_minute), tzinfo=timezone
            )
        is_open = start <= now < end
        conv.log.info("Hours check result", now=now.isoformat(), is_open=is_open)
        return is_open
    except Exception as e:
        conv.log.warning(
            "Failed to parse hours string, treating as open",
            hours_str=hours_str,
            error=str(e),
        )
        return True
