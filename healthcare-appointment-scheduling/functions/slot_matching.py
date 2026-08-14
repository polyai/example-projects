"""Slot matching and formatting helpers for appointment booking and rescheduling."""

from _gen import *  # <AUTO GENERATED>
import re
from datetime import UTC, datetime, timedelta
from typing import Optional


from .nextgen_response_models import AppointmentSlot


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


# ---------------------------------------------------------------------------
# Slot selection
# ---------------------------------------------------------------------------


def select_best_slot(
    slots: list[AppointmentSlot],
) -> Optional[AppointmentSlot]:
    """Pick the earliest available slot."""
    if not slots:
        return None
    candidates: list[tuple[datetime, AppointmentSlot]] = []
    for slot in slots:
        parsed = _parse_datetime_like(str(slot.start_date or ""))
        if parsed is not None:
            candidates.append((parsed, slot))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def select_closest_slot(
    requested_date: Optional[str],
    requested_time: Optional[str],
    slots: list[AppointmentSlot],
    now: Optional[datetime] = None,
) -> Optional[AppointmentSlot]:
    """Pick the best slot for normalized date/time preferences.

    When no preference is given, returns the earliest slot.
    """
    if not slots:
        return None

    reference_now = now or datetime.now(UTC)
    today = reference_now.date()

    # Parse date preference
    target_date = None
    date_text = str(requested_date or "").strip().lower()
    if date_text:
        parsed_dt = _parse_datetime_like(date_text)
        if parsed_dt:
            target_date = parsed_dt.date()
        elif date_text == "today":
            target_date = today
        elif date_text == "tomorrow":
            target_date = today + timedelta(days=1)

    # Parse time preference
    target_minutes = None
    time_text = str(requested_time or "").strip().lower()
    if time_text:
        if "morning" in time_text:
            target_minutes = 9 * 60
        elif "afternoon" in time_text:
            target_minutes = 14 * 60
        elif "evening" in time_text:
            target_minutes = 18 * 60
        else:
            m = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", time_text)
            if m:
                h = int(m.group(1))
                mi = int(m.group(2) or "0")
                mer = m.group(3)
                if mer:
                    if h == 12:
                        h = 0
                    if mer == "pm":
                        h += 12
                if 0 <= h <= 23 and 0 <= mi <= 59:
                    target_minutes = h * 60 + mi

    candidates: list[tuple[int, datetime, AppointmentSlot]] = []
    for slot in slots:
        parsed = _parse_datetime_like(str(slot.start_date or ""))
        if parsed is None:
            continue
        penalty = 0
        if target_date:
            penalty += abs((parsed.date() - target_date).days) * 100
        if target_minutes is not None:
            slot_minutes = parsed.hour * 60 + parsed.minute
            penalty += abs(slot_minutes - target_minutes)
        candidates.append((penalty, parsed, slot))

    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], item[1]))
    return candidates[0][2]


def get_next_available_slot(slots: list[AppointmentSlot]) -> Optional[AppointmentSlot]:
    """Return the earliest valid slot (no preferences)."""
    return select_best_slot(slots)


def get_top_n_available_slots(
    slots: list[AppointmentSlot], n: int = 2
) -> list[AppointmentSlot]:
    """Return up to n earliest available slots."""
    result: list[AppointmentSlot] = []
    remaining = list(slots)
    for _ in range(n):
        slot = select_best_slot(remaining)
        if slot is None:
            break
        result.append(slot)
        remaining = [
            s
            for s in remaining
            if str(s.start_date or "") != str(slot.start_date or "")
        ]
    return result


def filter_slots_by_lead_time(
    slots: list[AppointmentSlot],
    now: datetime,
    lead_minutes: int = 60,
) -> list[AppointmentSlot]:
    """Remove slots that start within *lead_minutes* of *now* (default 60)."""
    cutoff = now + timedelta(minutes=lead_minutes)
    result: list[AppointmentSlot] = []
    for slot in slots:
        parsed = _parse_datetime_like(str(slot.start_date or ""))
        if parsed is None:
            result.append(slot)
            continue
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        if parsed >= cutoff:
            result.append(slot)
    return result


# ---------------------------------------------------------------------------
# Display formatting
# ---------------------------------------------------------------------------

_RESOURCE_NAME_PREFIXES = {"FP", "IM", "NP", "PA", "DO", "MD"}


def _strip_resource_prefix(name: str) -> str:
    """Strip department/credential prefixes like 'FP' from resource display names."""
    parts = name.split(None, 1)
    if len(parts) == 2 and parts[0].upper() in _RESOURCE_NAME_PREFIXES:
        return parts[1]
    return name


def format_slot_display(
    slot: AppointmentSlot, provider_name: Optional[str] = None
) -> str:
    """Format a slot into a TTS-friendly string like 'Monday, April 7 at 2 PM with Dr. Smith'."""
    raw = str(slot.start_date or "").strip()
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        weekday = dt.strftime("%A")
        month = dt.strftime("%B")
        day = dt.day
        hour, minute = dt.hour, dt.minute
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


def format_slot_offer_display(slots: list[AppointmentSlot]) -> str:
    """Format a list of offered slots into a natural TTS-friendly string."""
    if not slots:
        return "an available time"
    if len(slots) == 1:
        return format_slot_display(slots[0])
    displays = [format_slot_display(s) for s in slots]
    if len(displays) == 2:
        return f"{displays[0]}, or {displays[1]}"
    return f"{', '.join(displays[:-1])}, or {displays[-1]}"


@func_description("Slot matching helper methods")
def slot_matching(conv: Conversation):
    """Entrypoint function stub for Agent Studio validation."""
    pass
