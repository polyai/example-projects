from _gen import *  # <AUTO GENERATED>
import calendar
from datetime import datetime, timedelta
from itertools import groupby
from typing import Optional


DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def _fmt_time(t: str) -> str:
    h, m = map(int, t.split(":"))
    period = "am" if h < 12 else "pm"
    h12 = h % 12 or 12
    return f"{h12}:{m:02d}{period}" if m else f"{h12}{period}"


def _fmt_hours(hours: str) -> str:
    start, end = hours.split("-")
    return f"{_fmt_time(start)} to {_fmt_time(end)}"


def _fmt_day_range(days: list[str]) -> str:
    if len(days) == 1:
        return days[0].capitalize()
    return f"{days[0].capitalize()} through {days[-1].capitalize()}"


def opening_hours_utterance(opening_hours: dict) -> str:
    """Convert an opening_hours config dict into a spoken utterance.

    Expects a dict mapping day names to "HH:MM-HH:MM" strings (or "closed").
    Consecutive days with the same hours are grouped into ranges. Closed days
    break a range so that e.g. Mon+Wed open with Tue closed won't produce
    "Monday through Wednesday".

    Example: {"monday": "07:00-19:00", "tuesday": "07:00-19:00", "saturday": "07:00-16:00"}
    -> "We're available Monday through Tuesday 7am to 7pm, and Saturday 7am to 4pm central time."

    Returns empty string when no opening hours are configured.
    """
    daily = {k: v for k, v in opening_hours.items() if isinstance(v, str)}

    # Build schedule including closed days so groupby breaks on them
    schedule = [(d, daily.get(d, "closed")) for d in DAYS]

    groups = []
    for hours, items in groupby(schedule, key=lambda x: x[1]):
        if hours.strip().lower() == "closed":
            continue
        days = [d for d, _ in items]
        groups.append((days, hours))

    if not groups:
        return ""

    parts = [f"{_fmt_day_range(days)} {_fmt_hours(hours)}" for days, hours in groups]

    if len(parts) == 1:
        return f"We're available {parts[0]} central time."
    if len(parts) == 2:
        return f"We're available {parts[0]}, and {parts[1]} central time."
    return f"We're available {', '.join(parts[:-1])}, and {parts[-1]} central time."


def get_prompt_for_appointment_timeframe_readback(
    appointment: dict, call_intent: str
) -> str:
    start = remove_seconds(appointment["start"])
    end = remove_seconds(appointment["end"])

    prompt = ""

    if start == "08:00" and end == "20:00":  # AT
        prompt += "(don't say anything about service time unless asked, as service time is between 8am and sunset)"
    elif start == "08:00" and end == "13:00":  # AM
        prompt += " - the field expert is currently scheduled to arrive at your property in the morning to early afternoon, between 8am and 1pm"
    elif start == "13:00" and end == "20:00":  # PM
        prompt += " - the field expert is currently scheduled to arrive at your property in the afternoon to early evening, between 1pm and sunset"
    else:  # Timed
        prompt += f" - the field expert is currently scheduled to arrive at your property between {start} and {end}"

    prompt += get_prompt_for_interior_vs_exterior_readback(
        appointment["doInterior"] == "2"
    )

    if call_intent == "reschedule":
        prompt += " - shall we go ahead with finding a new time for your appointment?"
    elif call_intent == "cancel":
        prompt += " - is that the appointment you wanted to cancel?"
    else:
        prompt += " - is that all okay?"

    return prompt


def get_prompt_for_interior_vs_exterior_readback(interior_needed: bool) -> str:
    if interior_needed:
        return " - since this includes indoor work, someone will need to be home to let the technician in"
    else:
        return ""


def get_prompt_for_new_appointment_timeframe_readback(start: str, end: str) -> str:
    prompt = ""

    if start == "08:00" and end == "20:00":  # AT
        prompt += "(don't say anything about service time unless asked, as service time is between 8am and sunset)"
    elif start == "08:00" and end == "13:00":  # AM
        prompt += " - in the morning to early afternoon, between 8am and 1pm"
    elif start == "13:00" and end == "20:00":  # PM
        prompt += " - in the afternoon to early evening, between 1pm and sunset"
    else:  # Timed
        prompt += f" - between {start} and {end}"

    return prompt


def get_start_and_end_date_for_search(requested_date: str, current_date: str) -> dict:
    """
    Given a requested_date and a current_date (both in "YYYY-MM-DD" format),
    returns a dict with "start_date" and "end_date" where:
      - start_date is no earlier than current_date + 1 day.
      - The ideal start_date is requested_date - 7 days.
      - The actual start_date is the later of the two dates above.
      - The end_date is exactly 14 days after the chosen start_date.
    """
    date_format = "%Y-%m-%d"
    requested_dt = datetime.strptime(requested_date, date_format).date()
    current_dt = datetime.strptime(current_date, date_format).date()

    min_start = current_dt + timedelta(days=1)
    ideal_start = requested_dt - timedelta(days=7)
    chosen_start = max(ideal_start, min_start)
    end_date = chosen_start + timedelta(days=14)

    return {
        "start_date": chosen_start.strftime(date_format),
        "end_date": end_date.strftime(date_format),
    }


def increment_date_by_one(date_str: str) -> str:
    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    next_day = date_obj + timedelta(days=1)
    return next_day.isoformat()


def remove_seconds(time_str: str) -> str:
    t = datetime.strptime(time_str, "%H:%M:%S").time()
    return t.strftime("%H:%M")


def dates_in_same_month(date1_str: str, date2_str: str) -> bool:
    date_format = "%Y-%m-%d"
    date1 = datetime.strptime(date1_str, date_format)
    date2 = datetime.strptime(date2_str, date_format)
    return date1.year == date2.year and date1.month == date2.month


def is_within_days(date1_str: str, date2_str: str, days: int) -> bool:
    """Return True if date1 and date2 are less than `days` days apart."""
    date_format = "%Y-%m-%d"
    d1 = datetime.strptime(date1_str, date_format).date()
    d2 = datetime.strptime(date2_str, date_format).date()
    return abs((d2 - d1).days) < days


def get_most_recent_date(date_list: list[str]) -> Optional[str]:
    if not date_list:
        return None
    return max(date_list, key=lambda d: datetime.strptime(d, "%Y-%m-%d"))


def is_more_than_months_ago(date_str: str, current_date_str: str, months: int) -> bool:
    """Return True if date_str is more than `months` calendar months before current_date_str."""
    date_format = "%Y-%m-%d"
    d = datetime.strptime(date_str, date_format).date()
    current = datetime.strptime(current_date_str, date_format).date()

    threshold_month = current.month - months
    threshold_year = current.year
    while threshold_month <= 0:
        threshold_month += 12
        threshold_year -= 1

    max_day = calendar.monthrange(threshold_year, threshold_month)[1]
    threshold = current.replace(
        year=threshold_year, month=threshold_month, day=min(current.day, max_day)
    )
    return d < threshold


def get_potential_slot(conv, **kwargs) -> Optional[dict]:
    """Slot-matching logic — only used in real API mode.

    In mock mode the callers (find_slot_availability, check_slot_availability) bypass
    this function entirely.  This stub exists so their imports remain valid.
    """
    raise NotImplementedError(
        "get_potential_slot requires a real dispatch API — "
        "implement route/capacity matching for your provider"
    )


@func_description("utils")
def utils(conv: Conversation):
    pass
