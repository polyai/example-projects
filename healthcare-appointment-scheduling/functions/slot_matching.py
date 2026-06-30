import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Optional

from _gen import *  # <AUTO GENERATED>

from .nextgen_response_models import AppointmentSlot


@dataclass
class _DatePreference:
    target_date: Optional[date] = None
    range_start: Optional[date] = None
    range_end: Optional[date] = None


@dataclass
class _TimePreference:
    mode: str = "none"  # none | target | after | before | earlier
    minute_value: Optional[int] = None


def _parse_datetime_like(value: str) -> Optional[datetime]:
    """Parse ISO-like datetime strings, including trailing Z."""
    text = str(value or "").strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _parse_requested_date(requested_date: Optional[str], now: datetime) -> _DatePreference:
    """Convert normalized date intent text into a date preference."""
    text = str(requested_date or "").strip().lower()
    if not text:
        return _DatePreference()

    parsed_dt = _parse_datetime_like(text)
    if parsed_dt is not None:
        return _DatePreference(target_date=parsed_dt.date())

    today = now.date()
    if text == "today":
        return _DatePreference(target_date=today)
    if text == "tomorrow":
        return _DatePreference(target_date=today + timedelta(days=1))
    if text in {"day after tomorrow", "overmorrow"}:
        return _DatePreference(target_date=today + timedelta(days=2))
    if text == "next week":
        start = today + timedelta(days=7)
        end = today + timedelta(days=13)
        return _DatePreference(range_start=start, range_end=end)

    weekday_to_index = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }
    if text in weekday_to_index:
        desired = weekday_to_index[text]
        delta = (desired - today.weekday()) % 7
        if delta == 0:
            delta = 7
        return _DatePreference(target_date=today + timedelta(days=delta))

    return _DatePreference()


def _parse_time_of_day_to_minutes(value: str) -> Optional[int]:
    """Parse textual times (e.g., 3pm, 15:30) into minutes from midnight."""
    text = value.strip().lower()
    if not text:
        return None

    text = text.replace(".", "")
    match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", text)
    if not match:
        return None

    hour = int(match.group(1))
    minute = int(match.group(2) or "0")
    meridiem = match.group(3)

    if meridiem:
        if hour == 12:
            hour = 0
        if meridiem == "pm":
            hour += 12
    if hour > 23 or minute > 59:
        return None

    return hour * 60 + minute


def _parse_requested_time(requested_time: Optional[str]) -> _TimePreference:
    """Convert normalized time intent text into a time preference."""
    text = str(requested_time or "").strip().lower()
    if not text:
        return _TimePreference()

    if "earlier" in text or "earliest" in text:
        return _TimePreference(mode="earlier")
    if "morning" in text:
        return _TimePreference(mode="target", minute_value=9 * 60)
    if "afternoon" in text:
        return _TimePreference(mode="target", minute_value=14 * 60)
    if "evening" in text:
        return _TimePreference(mode="target", minute_value=18 * 60)

    after_match = re.search(r"after\s+(.+)$", text)
    if after_match:
        boundary = _parse_time_of_day_to_minutes(after_match.group(1))
        if boundary is not None:
            return _TimePreference(mode="after", minute_value=boundary)

    before_match = re.search(r"before\s+(.+)$", text)
    if before_match:
        boundary = _parse_time_of_day_to_minutes(before_match.group(1))
        if boundary is not None:
            return _TimePreference(mode="before", minute_value=boundary)

    at_match = re.search(r"(at|around)\s+(.+)$", text)
    if at_match:
        minute_value = _parse_time_of_day_to_minutes(at_match.group(2))
        if minute_value is not None:
            return _TimePreference(mode="target", minute_value=minute_value)

    raw_time = _parse_time_of_day_to_minutes(text)
    if raw_time is not None:
        return _TimePreference(mode="target", minute_value=raw_time)

    return _TimePreference()


def _date_penalty(slot_day: date, pref: _DatePreference) -> int:
    """Compute date distance penalty for a slot day."""
    if pref.range_start and pref.range_end:
        if pref.range_start <= slot_day <= pref.range_end:
            return 0
        if slot_day < pref.range_start:
            return (pref.range_start - slot_day).days * 100
        return (slot_day - pref.range_end).days * 100

    if pref.target_date:
        return abs((slot_day - pref.target_date).days) * 100

    return 0


def _time_penalty(minutes: int, pref: _TimePreference) -> int:
    """Compute time distance penalty for a slot minute-of-day."""
    if pref.mode == "none":
        return 0
    if pref.mode == "earlier":
        return minutes
    if pref.mode == "target" and pref.minute_value is not None:
        return abs(minutes - pref.minute_value)
    if pref.mode == "after" and pref.minute_value is not None:
        if minutes >= pref.minute_value:
            return minutes - pref.minute_value
        return 1000 + (pref.minute_value - minutes)
    if pref.mode == "before" and pref.minute_value is not None:
        if minutes <= pref.minute_value:
            return pref.minute_value - minutes
        return 1000 + (minutes - pref.minute_value)
    return 0


def select_closest_slot(
    requested_date: Optional[str],
    requested_time: Optional[str],
    slots: list[AppointmentSlot],
    now: Optional[datetime] = None,
) -> Optional[AppointmentSlot]:
    """Pick the best slot for normalized requested date/time preferences."""
    if not slots:
        return None

    reference_now = now or datetime.now(UTC)
    date_pref = _parse_requested_date(requested_date, reference_now)
    time_pref = _parse_requested_time(requested_time)

    candidates: list[tuple[int, datetime, AppointmentSlot]] = []
    for slot in slots:
        parsed = _parse_datetime_like(str(slot.start_date or ""))
        if parsed is None:
            continue

        minutes = parsed.hour * 60 + parsed.minute
        total_penalty = _date_penalty(parsed.date(), date_pref) + _time_penalty(minutes, time_pref)
        candidates.append((total_penalty, parsed, slot))

    if not candidates:
        return None

    candidates.sort(key=lambda item: (item[0], item[1]))
    return candidates[0][2]


def filter_slots_by_lead_time(
    slots: list[AppointmentSlot],
    now: datetime,
    lead_minutes: int = 60,
) -> list[AppointmentSlot]:
    """Remove slots that start within *lead_minutes* of *now* (default 60).

    Combines the date from ``startDate`` with the time from ``beginTime``
    (4-digit HHMM, e.g. ``"0830"`` = 8:30 AM, ``"1630"`` = 4:30 PM) to get
    the actual slot start datetime. Slots with no parseable date are kept.
    """
    cutoff = now + timedelta(minutes=lead_minutes)
    result: list[AppointmentSlot] = []
    for slot in slots:
        parsed = _parse_datetime_like(str(slot.start_date or ""))
        if parsed is None:
            result.append(slot)
            continue
        # Override the time component using beginTime (HHMM) when present.
        begin = str(slot.begin_time or "").strip()
        if begin:
            digits = "".join(ch for ch in begin if ch.isdigit())
            if len(digits) == 3:
                digits = f"0{digits}"
            if len(digits) >= 4:
                hour = int(digits[0:2])
                minute = int(digits[2:4])
                if 0 <= hour <= 23 and 0 <= minute <= 59:
                    parsed = parsed.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        if parsed >= cutoff:
            result.append(slot)
    return result


def get_next_available_slot(slots: list[AppointmentSlot]) -> Optional[AppointmentSlot]:
    """Return the earliest valid slot when no preferences are provided."""
    return select_closest_slot(requested_date=None, requested_time=None, slots=slots)


def get_top_n_available_slots(slots: list[AppointmentSlot], n: int = 2) -> list[AppointmentSlot]:
    """Return up to n earliest available slots."""
    result: list[AppointmentSlot] = []
    remaining = list(slots)
    for _ in range(n):
        slot = get_next_available_slot(remaining)
        if slot is None:
            break
        result.append(slot)
        remaining = [s for s in remaining if str(s.start_date or "") != str(slot.start_date or "")]
    return result


def get_top_n_preference_slots(
    requested_date: Optional[str],
    requested_time: Optional[str],
    slots: list[AppointmentSlot],
    n: int = 2,
) -> list[AppointmentSlot]:
    """Return up to n slots best matching the given preference. Returns [] if no match at all."""
    result: list[AppointmentSlot] = []
    remaining = list(slots)
    for _ in range(n):
        slot = select_closest_slot(
            requested_date=requested_date, requested_time=requested_time, slots=remaining
        )
        if slot is None:
            break
        result.append(slot)
        remaining = [s for s in remaining if str(s.start_date or "") != str(slot.start_date or "")]
    return result


def format_slot_offer_display(slots: list[AppointmentSlot]) -> str:
    """Format a list of offered slots into a natural TTS-friendly string.

    When all slots share the same provider and location, collapses into a
    compact form like "9:15 AM or 11:30 AM on Monday, April 7 with Dr. Smith
    at Main Clinic".
    """
    if not slots:
        return "an available time"
    if len(slots) == 1:
        return format_slot_display(slots[0])

    compact = _try_compact_display(slots)
    if compact:
        return compact

    displays = [format_slot_display(s) for s in slots]
    if len(displays) == 2:
        return f"{displays[0]}, or {displays[1]}"
    return f"{', '.join(displays[:-1])}, or {displays[-1]}"


def _try_compact_display(slots: list[AppointmentSlot]) -> str | None:
    """If all slots share the same date, provider, and location, return a compact display."""
    from datetime import datetime

    def _resolve_name(s: AppointmentSlot) -> str:
        name = s.resource_name or (s.resource_names[0] if s.resource_names else "")
        return _strip_resource_prefix(name) if name else ""

    providers = {_resolve_name(s) for s in slots}
    locations = {(s.location_name or "") for s in slots}
    dates: set[str] = set()
    time_parts: list[str] = []

    for s in slots:
        raw = str(s.start_date or "").strip()
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            dates.add(dt.strftime("%Y-%m-%d"))
            hour, minute = dt.hour, dt.minute
            if hour == 0:
                time_parts.append(f"12:{minute:02d} AM" if minute else "midnight")
            elif hour < 12:
                time_parts.append(f"{hour}:{minute:02d} AM" if minute else f"{hour} AM")
            elif hour == 12:
                time_parts.append(f"12:{minute:02d} PM" if minute else "noon")
            else:
                h = hour - 12
                time_parts.append(f"{h}:{minute:02d} PM" if minute else f"{h} PM")
        except Exception:
            return None

    if len(providers) != 1 or len(locations) != 1 or len(dates) != 1:
        return None

    raw = str(slots[0].start_date or "").strip()
    dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    date_str = f"{dt.strftime('%A')}, {dt.strftime('%B')} {dt.day}"

    if len(time_parts) == 2:
        times = f"{time_parts[0]} or {time_parts[1]}"
    else:
        times = f"{', '.join(time_parts[:-1])}, or {time_parts[-1]}"

    result = f"{times} on {date_str}"
    provider = providers.pop()
    location = locations.pop()
    if provider:
        result = f"{result} with {provider}"
    if location:
        result = f"{result} at {location}"
    return result


_RESOURCE_NAME_PREFIXES = {"FP", "IM", "NP", "PA", "DO", "MD"}


def _strip_resource_prefix(name: str) -> str:
    """Strip department/credential prefixes like 'FP' from resource display names."""
    parts = name.split(None, 1)
    if len(parts) == 2 and parts[0].upper() in _RESOURCE_NAME_PREFIXES:
        return parts[1]
    return name


def format_slot_display(slot: AppointmentSlot, provider_name: Optional[str] = None) -> str:
    """Format a slot's start_date into a TTS-friendly string like 'Monday, April 7 at 2 PM with Dr. Smith'."""
    from datetime import datetime

    raw = str(slot.start_date or "").strip()
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        weekday = dt.strftime("%A")
        month = dt.strftime("%B")
        day = dt.day
        hour = dt.hour
        minute = dt.minute
        if hour == 0:
            time_str = f"12:{minute:02d} AM" if minute else "midnight"
        elif hour < 12:
            time_str = f"{hour}:{minute:02d} AM" if minute else f"{hour} AM"
        elif hour == 12:
            time_str = f"12:{minute:02d} PM" if minute else "noon"
        else:
            h = hour - 12
            time_str = f"{h}:{minute:02d} PM" if minute else f"{h} PM"
        display = f"{weekday}, {month} {day} at {time_str}"
    except Exception:
        display = raw or "an available time"
    # Resolve provider name: prefer explicit arg, then slot resource_name
    name = (
        provider_name
        or slot.resource_name
        or (slot.resource_names[0] if slot.resource_names else None)
    )
    if name:
        name = _strip_resource_prefix(name)
        display = f"{display} with {name}"
    if slot.location_name:
        display = f"{display} at {slot.location_name}"
    return display


@func_description("Slot matching helper methods")
def slot_matching(conv: Conversation):
    """Entrypoint function stub for Agent Studio validation."""
    pass
