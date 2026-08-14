"""Shared helpers for selecting and filtering appointments (cancel/reschedule/booking)."""

from _gen import *  # <AUTO GENERATED>
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Optional

from functions.nextgen_response_models import Appointment

# EHR event IDs per appointment type -- used when the slot has no event_id.
EVENT_ID_BY_APPOINTMENT_TYPE: dict[str, str] = {
    "ill": "0e38e7a7-fcaa-447c-9ff6-b5255bc9c226",
    "recheck": "b5c6d1f8-1820-4c47-ad1a-d6e5e61c8d90",
    "wellness": "c12a3b4d-5678-9abc-def0-123456789abc",
}
FOLLOW_UP_EVENT_ID = EVENT_ID_BY_APPOINTMENT_TYPE["recheck"]

_APPOINTMENT_TYPE_LABELS: dict[str, str] = {
    "ill": "sick visit",
    "recheck": "recheck",
    "wellness": "wellness check",
}
_EVENT_ID_TO_TYPE = {v.lower(): k for k, v in EVENT_ID_BY_APPOINTMENT_TYPE.items()}

# Recheck types that use recall-based windowing.
RECHECK_TYPES = {"recheck"}


def appointment_type_label(event_id: str | None) -> str:
    """Return a caller-friendly label for an event_id, or 'appointment' as fallback."""
    if not event_id:
        return "appointment"
    appt_type = _EVENT_ID_TO_TYPE.get(str(event_id).lower())
    return (
        _APPOINTMENT_TYPE_LABELS.get(appt_type, "appointment")
        if appt_type
        else "appointment"
    )


# ---------------------------------------------------------------------------
# Date / datetime parsing helpers
# ---------------------------------------------------------------------------


def normalize_iso_date_prefix(value: Optional[str]) -> Optional[str]:
    """Return YYYY-MM-DD prefix from an ISO-like datetime string, or None."""
    if value is None:
        return None
    s = str(value).strip()
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return None


def parse_utc_datetime(value: Optional[str]) -> Optional[datetime]:
    """Parse appointment API datetime to an aware UTC datetime (best effort)."""
    if not value:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    except ValueError:
        return None


def normalize_entity_date_to_yyyy_mm_dd(value: object) -> Optional[str]:
    """Normalize a date entity (date object or spoken string) to YYYY-MM-DD."""
    if value is None:
        return None
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        try:
            return isoformat()[:10]
        except Exception:
            pass
    s = str(value).strip()
    if not s:
        return None
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    digits = re.sub(r"\D", "", s)
    if len(digits) == 8:
        y1 = int(digits[:4])
        if 1900 <= y1 <= 2100:
            return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"
        return f"{digits[4:8]}-{digits[:2]}-{digits[2:4]}"
    return s[:10] if len(s) >= 10 else None


# ---------------------------------------------------------------------------
# Appointment filtering
# ---------------------------------------------------------------------------


def get_active_appointments(
    appointments: list[Appointment],
    now_utc: Optional[datetime] = None,
) -> list[Appointment]:
    """Return future, non-cancelled appointments."""
    now = now_utc or datetime.now(UTC)
    return [
        a
        for a in appointments
        if a.is_cancelled is not True
        and parse_utc_datetime(a.appointment_date) is not None
        and parse_utc_datetime(a.appointment_date).date() >= now.date()
    ]


# Alias kept for cancel/reschedule flow compatibility.
filter_upcoming_active = get_active_appointments


def is_follow_up_appointment(appointment: Appointment) -> bool:
    """Check if an appointment is a known follow-up type."""
    eid = appointment.event_id
    if not eid:
        return False
    known = {v.lower() for v in EVENT_ID_BY_APPOINTMENT_TYPE.values()}
    return str(eid).lower() in known


# ---------------------------------------------------------------------------
# Appointment matching for cancel/reschedule flows
# ---------------------------------------------------------------------------


def match_appointments_on_calendar_day(
    appointments: list[Appointment], calendar_day_yyyy_mm_dd: str
) -> list[Appointment]:
    """Return appointments whose date falls on the given calendar day."""
    target = normalize_iso_date_prefix(calendar_day_yyyy_mm_dd)
    if not target:
        return []
    return [
        a
        for a in appointments
        if normalize_iso_date_prefix(
            str(a.appointment_date) if a.appointment_date else None
        )
        == target
    ]


def find_appointments_by_month_day(
    appointments: list[Appointment], month: int, day: int
) -> list[Appointment]:
    """Match loaded appointments by calendar month and day."""
    result: list[Appointment] = []
    for a in appointments:
        p = normalize_iso_date_prefix(
            str(a.appointment_date) if a.appointment_date else None
        )
        if not p or len(p) < 10:
            continue
        try:
            if int(p[5:7]) == month and int(p[8:10]) == day:
                result.append(a)
        except ValueError:
            continue
    return result


def resolve_cancel_appointments_from_date_parts(
    appointments: list[Appointment],
    day_str: str,
    month_str: str,
    year_str: str,
) -> tuple[list[Appointment], str | None]:
    """Match appointments from structured day/month/year strings.

    Returns (matches, error_key). error_key is 'missing_day_or_month',
    'invalid_components', or None.
    """
    day_str = str(day_str).strip()
    month_str = str(month_str).strip()
    year_str = str(year_str).strip()
    if not day_str or day_str.lower() in ("na", "n/a"):
        return [], "missing_day_or_month"
    if not month_str or month_str.lower() in ("na", "n/a"):
        return [], "missing_day_or_month"
    try:
        day_i = int(day_str)
        month_i = int(month_str)
    except ValueError:
        return [], "invalid_components"
    if not (1 <= month_i <= 12 and 1 <= day_i <= 31):
        return [], "invalid_components"

    if not year_str or year_str.lower() in ("na", "n/a"):
        return find_appointments_by_month_day(appointments, month_i, day_i), None

    try:
        year_i = int(year_str)
    except ValueError:
        return [], "invalid_components"
    try:
        resolved = date(year_i, month_i, day_i).isoformat()
    except ValueError:
        return [], "invalid_components"
    return match_appointments_on_calendar_day(appointments, resolved), None


# ---------------------------------------------------------------------------
# Recall-plan helpers (used by reschedule flow)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RecallWindowResult:
    """Result of looking up the recall-based booking window."""

    ok: bool
    start_iso: Optional[str] = None
    end_iso: Optional[str] = None
    expected_return_date: Optional[str] = None
    needs_disambiguation: bool = False
    disambiguation_options: Optional[list[dict]] = None
    resolved_appointment_type: Optional[str] = None


def is_recheck_type(appointment_type: str) -> bool:
    """Return True if the appointment type should use recall-based windowing."""
    return appointment_type in RECHECK_TYPES


def get_recall_window(conv: Conversation, appointment_type: str) -> RecallWindowResult:
    """Fetch recall plans and return a date window around expectedReturnDate.

    Simplified for the template -- returns a 90-day window from today.
    """
    now = date.today()
    start_iso = now.strftime("%Y-%m-%dT00:00:00")
    end_iso = (now + timedelta(days=90)).strftime("%Y-%m-%dT23:59:59")
    return RecallWindowResult(
        ok=True,
        start_iso=start_iso,
        end_iso=end_iso,
        expected_return_date=now.isoformat(),
    )


@func_description("Shared helpers for selecting appointments (cancel/reschedule)")
def appointment_selection(conv: Conversation):
    """Helpers to select and qualify appointments for cancel/reschedule flows."""
