"""Practice management (EHR) API client: patients, appointments and open slots.

Every tool reads and writes through this module, so connecting a real EHR means
replacing the bodies of the helpers below and nothing else.

Mock or real (see use_mock_api):
- branch, draft and sandbox always use the mock, so a test call never touches
  a real system;
- pre-release and live use the mock until the real API is connected and
  `settings.use_mock_api` is set to false in real-time config.

The mock keeps every change a call makes (bookings, moves, cancellations) in
conv.state, so two test calls never see each other's bookings. The seed data
is rebuilt from the functions below on every read and never mutated.

Fixtures (strict ID&V: phone + date of birth + member ID):
- Jane Smith, 201-555-0123, born 1985-03-15, member ID HC48213: a follow-up
  with the first provider (Dr. Smith by default) on the fourth open day from today, 10am
- John Doe, 212-555-0178, born 1990-07-22, member ID HC77306: a follow-up with
  the first provider (fifth open day, 9am) and a sick visit with the second
  (Dr. Johnson by default; seventh open day, 2pm)
- 201-555-0199: no patient
"""

import re
import uuid
from datetime import date, timedelta

from _gen import *  # <AUTO GENERATED>

LIVE_ENVS = ("pre-release", "pre_release", "live")

APPOINTMENT_TYPES = ["Sick visit", "Follow-up", "Wellness check"]

# Appointment start times the mock offers on each day the clinic is open.
SLOT_TIMES = ["09:00", "10:30", "14:00", "15:30"]
SLOT_MINUTES = 30
SEARCH_DAYS = 21

# Used when the providers variant attribute is blank.
DEFAULT_PROVIDERS = ["Dr. Smith", "Dr. Johnson"]


@func_description("[UTIL] EHR API client, not callable directly")
def api_client(conv: Conversation):
    return "EHR API client module."


# --- Mock or real ---------------------------------------------------------


def use_mock_api(conv) -> bool:
    if (conv.env or "").lower() not in LIVE_ENVS:
        return True
    return bool(
        (conv.real_time_config or {}).get("settings", {}).get("use_mock_api", True)
    )


def _real_api_missing(name: str):
    raise NotImplementedError(
        f"{name}: connect your EHR API here, or keep settings.use_mock_api on"
    )


# --- Seed data --------------------------------------------------------------


def _today(conv=None) -> date:
    try:
        return date.fromisoformat(conv.state.today_iso)
    except (AttributeError, TypeError, ValueError):
        return date.today()


def _nth_open_day(conv, n: int) -> date:
    from functions.appointments import open_weekdays

    open_days = open_weekdays(conv) or {0, 1, 2, 3, 4}
    count, day = 0, _today(conv)
    while count < n:
        day += timedelta(days=1)
        if day.weekday() in open_days:
            count += 1
    return day


def providers(conv) -> dict[str, str]:
    """Provider id -> name. The mock's providers are the ones named in the
    `providers` variant attribute (comma-separated), so a clinic's own clinicians
    are offered from the first test call."""
    text = (getattr(conv.variant, "providers", "") if conv.variant else "") or ""
    names = [n.strip() for n in text.split(",") if n.strip()] or DEFAULT_PROVIDERS
    return {f"MOCK-R{i + 1:03d}": name for i, name in enumerate(names)}


def _provider_id(conv, wanted: str) -> str:
    known = providers(conv)
    return wanted if wanted in known else next(iter(known))


def _patients() -> list[dict]:
    return [
        {
            "id": "MOCK-P001",
            "first_name": "Jane",
            "last_name": "Smith",
            "dob": "1985-03-15",
            "member_id": "HC48213",
            "phone": "2015550123",
            "provider_id": "MOCK-R001",
        },
        {
            "id": "MOCK-P002",
            "first_name": "John",
            "last_name": "Doe",
            "dob": "1990-07-22",
            "member_id": "HC77306",
            "phone": "2125550178",
            "provider_id": "MOCK-R002",
        },
    ]


def _appointment(conv, appt_id, patient_id, kind, open_day, start, provider_id) -> dict:
    return {
        "id": appt_id,
        "patient_id": patient_id,
        "type": kind,
        "reason": "",
        "date": _nth_open_day(conv, open_day).isoformat(),
        "start": start,
        "provider_id": _provider_id(conv, provider_id),
        "provider": providers(conv)[_provider_id(conv, provider_id)],
        "status": "Scheduled",
    }


def _seed_appointments(conv) -> list[dict]:
    return [
        _appointment(
            conv, "MOCK-A001", "MOCK-P001", "Follow-up", 4, "10:00", "MOCK-R001"
        ),
        _appointment(
            conv, "MOCK-A002", "MOCK-P002", "Follow-up", 5, "09:00", "MOCK-R001"
        ),
        _appointment(
            conv, "MOCK-A003", "MOCK-P002", "Sick visit", 7, "14:00", "MOCK-R002"
        ),
    ]


def _changes(conv) -> dict:
    """This call's bookings, moves and cancellations, kept in conv.state."""
    changes = conv.state.mock_changes
    if not isinstance(changes, dict):
        changes = {"created": [], "moved": {}, "cancelled": []}
        conv.state.mock_changes = changes
    return changes


def _normalise_phone(value) -> str:
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits


# --- Patients ---------------------------------------------------------------


def find_patients_by_phone(conv, phone: str) -> list[dict]:
    """Every patient record on this phone number (an empty list when there is none).

    Records carry dob (YYYY-MM-DD) and member_id, as functions/idnv.py expects."""
    if not use_mock_api(conv):
        _real_api_missing("find_patients_by_phone")
    digits = _normalise_phone(phone)
    return [dict(p) for p in _patients() if p["phone"] == digits]


def appointment_types(conv) -> list[str]:
    if not use_mock_api(conv):
        _real_api_missing("appointment_types")
    return list(APPOINTMENT_TYPES)


# --- Appointments -----------------------------------------------------------


def _live_appointments(conv) -> list[dict]:
    changes = _changes(conv)
    live = []
    for appt in _seed_appointments(conv) + [dict(a) for a in changes["created"]]:
        if appt["id"] in changes["cancelled"]:
            continue
        live.append({**appt, **changes["moved"].get(appt["id"], {})})
    return live


def list_appointments(conv, patient_id: str) -> list[dict]:
    """Upcoming appointments for a patient, soonest first."""
    if not use_mock_api(conv):
        _real_api_missing("list_appointments")
    mine = [a for a in _live_appointments(conv) if a["patient_id"] == patient_id]
    return sorted(mine, key=lambda a: (a["date"], a["start"]))


def open_slots(
    conv, start: date, provider_id: str = "", days: int = SEARCH_DAYS
) -> list[dict]:
    """Open appointment slots from `start` for `days` days, soonest first.

    The mock offers SLOT_TIMES on every day the clinic is open (opening_hours
    attribute), inside its hours, minus anything already booked with the same
    provider.
    """
    if not use_mock_api(conv):
        _real_api_missing("open_slots")
    from functions.appointments import hours_for_day

    provider_id = _provider_id(conv, provider_id)
    name = providers(conv)[provider_id]
    taken = {
        (a["date"], a["start"])
        for a in _live_appointments(conv)
        if a["provider_id"] == provider_id
    }
    slots = []
    for offset in range(days):
        day = start + timedelta(days=offset)
        hours = hours_for_day(conv, day)
        if not hours:
            continue
        opens, closes = hours
        for begin in SLOT_TIMES:
            if not opens <= begin < closes or (day.isoformat(), begin) in taken:
                continue
            slots.append(
                {
                    "date": day.isoformat(),
                    "start": begin,
                    "minutes": SLOT_MINUTES,
                    "provider_id": provider_id,
                    "provider": name,
                }
            )
    return slots


def create_appointment(
    conv, patient_id: str, slot: dict, kind: str, reason: str
) -> dict:
    """Book a slot. Returns the new appointment."""
    if not use_mock_api(conv):
        _real_api_missing("create_appointment")
    appt = {
        "id": f"MOCK-A-{uuid.uuid4().hex[:6].upper()}",
        "patient_id": patient_id,
        "type": kind,
        "reason": reason or "",
        "date": slot["date"],
        "start": slot["start"],
        "provider_id": slot["provider_id"],
        "provider": slot["provider"],
        "status": "Scheduled",
    }
    changes = _changes(conv)
    changes["created"] = changes["created"] + [appt]
    conv.state.mock_changes = changes
    return dict(appt)


def move_appointment(conv, appointment_id: str, slot: dict) -> bool:
    if not use_mock_api(conv):
        _real_api_missing("move_appointment")
    changes = _changes(conv)
    moved = dict(changes["moved"])
    moved[appointment_id] = {
        "date": slot["date"],
        "start": slot["start"],
        "provider_id": slot["provider_id"],
        "provider": slot["provider"],
    }
    changes["moved"] = moved
    conv.state.mock_changes = changes
    return True


def cancel_appointment(conv, appointment_id: str, reason: str) -> bool:
    if not use_mock_api(conv):
        _real_api_missing("cancel_appointment")
    changes = _changes(conv)
    changes["cancelled"] = changes["cancelled"] + [appointment_id]
    conv.state.mock_changes = changes
    conv.log.info("Mock cancellation", appointment_id=appointment_id, reason=reason)
    return True
