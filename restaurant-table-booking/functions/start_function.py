import datetime as dt
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import plog

from _gen import *  # <AUTO GENERATED>
from functions.try_transfer_call import is_restaurant_ooh


def _ordinal_suffix(day: int) -> str:
    """Return ordinal suffix only: 'st', 'nd', 'rd', or 'th' (e.g. for 1->st, 2->nd)."""
    if 11 <= day <= 13:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")


def ordinal_suffix(day):
    """Return full ordinal string for a day (e.g. 1st, 2nd, 21st)."""
    return f"{day}{_ordinal_suffix(day)}"


def get_named_dates(conv, _country="us"):
    """Return a formatted string of upcoming US holidays for the next ~12 months.

    Uses fixed dates and simple weekday rules (no Easter calculation).
    The _country parameter is kept for call-site compatibility but only US is supported.
    """
    tz = ZoneInfo(conv.variant.timezone)
    today = dt.datetime.now(tz).date()
    year = today.year
    next_year = year + 1

    def _nth_weekday(y, month, weekday, n):
        """Get the nth occurrence of weekday (0=Mon) in month."""
        count = 0
        for d in range(1, 32):
            try:
                candidate = dt.date(y, month, d)
            except ValueError:
                break
            if candidate.weekday() == weekday:
                count += 1
                if count == n:
                    return candidate
        return None

    def _last_weekday(y, month, weekday):
        """Get the last occurrence of weekday (0=Mon) in month."""
        last = (
            dt.date(y, month + 1, 1) - dt.timedelta(days=1)
            if month < 12
            else dt.date(y, 12, 31)
        )
        while last.weekday() != weekday:
            last -= dt.timedelta(days=1)
        return last

    def _holidays(y):
        return [
            (dt.date(y, 1, 1), "New Year's Day"),
            (_last_weekday(y, 5, 0), "Memorial Day"),
            (dt.date(y, 7, 4), "Independence Day"),
            (_nth_weekday(y, 9, 0, 1), "Labor Day"),
            (_nth_weekday(y, 11, 3, 4), "Thanksgiving"),
            (dt.date(y, 12, 24), "Christmas Eve"),
            (dt.date(y, 12, 25), "Christmas Day"),
            (dt.date(y, 12, 31), "New Year's Eve"),
        ]

    def _fmt(d, name):
        ordinal = f"{d.day}{_ordinal_suffix(d.day)}"
        iso = d.strftime("%Y-%m-%d")
        return f"[{iso} {name} ({ordinal} of {d.strftime('%B %Y')})]"

    holidays = [
        (d, n) for y in (year, next_year) for d, n in _holidays(y) if d >= today
    ]
    holidays.sort(key=lambda x: x[0])
    return ", ".join(_fmt(d, n) for d, n in holidays)


def set_datetime(conv: Conversation):
    now = dt.datetime.now(ZoneInfo(conv.variant.timezone))
    conv.state.now = now.isoformat()
    conv.state.current_date = now.strftime("%A %d-%m-%Y")
    conv.state.current_weekday = now.strftime("%A")
    conv.state.current_time = now.strftime("%H:%M")
    conv.state.formatted_date_time = now.strftime("%A, %B %d, %Y at %I:%M %p")


def parse_hours_from_text(hours_text):
    """Parse a multi-line "Day: hours" string into a {weekday: hours} dict.

    Falls back to default hours if the input is empty or unparseable.
    """
    hours_dict = {}
    for line in hours_text.strip().splitlines():
        if not line.strip():
            continue
        try:
            day, hours = line.split(":", 1)
            hours_dict[day.strip()] = hours.strip()
        except ValueError:
            continue
    if not hours_dict:
        hours_dict = {
            "Monday": "closed",
            "Tuesday": "11:00-22:00",
            "Wednesday": "11:00-22:00",
            "Thursday": "11:00-22:00",
            "Friday": "11:00-00:00",
            "Saturday": "11:00-22:00",
            "Sunday": "11:00-22:00",
        }
    return hours_dict


def load_site_real_time_config(conv):
    """Load opening hours from variant attributes."""
    if conv.variant.opening_hours:
        conv.state.site_opening_hours = parse_hours_from_text(
            conv.variant.opening_hours
        )
        conv.state.special_dates = {}
        plog.info(f"Opening Hours: {conv.state.site_opening_hours}")
        return

    conv.state.site_opening_hours = {}
    conv.state.special_dates = {}
    plog.warning("No opening hours configured in variant attributes")


def walk_in_only(conv):
    """Disable bookings when the restaurant ID is not numeric."""
    return not conv.variant.rid.strip().isdigit()


def start_function(conv: Conversation):
    try:
        ZoneInfo(conv.variant.timezone)
    except ZoneInfoNotFoundError:
        conv.variant.timezone = "America/New_York"
        conv.log.warning(
            "Using default timezone because the variant attribute is not valid.",
            timezone=conv.variant.timezone,
        )

    conv.state.special_date_greeting_message = ""
    conv.state.start_checking_availability_delay_utterance = (
        "Let me just check what space we have..."
    )

    # Feature flags
    conv.state.include_experiences = False
    conv.state.table_type_selection_enabled = True
    conv.state.disable_booking = walk_in_only(conv)

    # Init booking state
    conv.state.user_bookings = None
    conv.state.available_times = None
    conv.state.phone_number = None
    conv.state.check_if_date_exists_delay_utterance = "Just a second."
    conv.state.formatted_experiences = ""
    conv.state.active_experiences = {}

    set_datetime(conv)
    conv.state.named_days = get_named_dates(conv, "us")

    # Set opening/kitchen/bar/staffed hours
    load_site_real_time_config(conv)

    # Check if today is a special date
    today_str = conv.state.now
    conv.state.special_date_greeting_message = ""
    if special_date := conv.state.special_dates.get(today_str):
        conv.state.special_date_greeting_message = (
            special_date.get("greeting_message") or ""
        )

    # Extract phone number from caller or SIP headers
    if conv.caller_number:
        conv.state.phone_number = conv.caller_number
    from_header = conv.sip_headers.get("From", "")
    match = re.search("sip:(.+?)@", from_header)
    if match:
        conv.state.phone_number = match.group(1)

    conv.write_metric("RESTAURANT_ID", conv.variant.rid, write_once=True)
    conv.write_metric("RESTAURANT_NAME", conv.variant_name, write_once=True)

    now = dt.datetime.fromisoformat(conv.state.now)
    conv.state.next_few_days = "\n".join(
        (now + dt.timedelta(days=i)).strftime(
            f"- %A {ordinal_suffix((now + dt.timedelta(days=i)).day)} of %B %Y"
        )
        for i in range(1, 14)
    )

    now = dt.datetime.now(ZoneInfo(conv.variant.timezone))
    if is_restaurant_ooh(conv, now):
        conv.write_metric("OOH", write_once=True)
