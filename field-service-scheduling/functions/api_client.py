"""Dispatch API client: customers, appointments and open arrival windows.

Every tool reads and writes through this module, so connecting a real dispatch
system means replacing the bodies of the helpers below and nothing else.

Mock or real (see use_mock_api):
- branch, draft and sandbox always use the mock, so a test call never touches
  a real system;
- pre-release and live use the mock until the real API is connected and
  `settings.use_mock_api` is set to false in real-time config.

The mock keeps every change a call makes (bookings, moves, cancellations) in
conv.state, so two test calls never see each other's bookings. The seed data
is rebuilt from the functions below on every read and never mutated.

Availability works like a dispatch API: asked about a day, it returns every open
arrival window from three working days before it (never before tomorrow) to three
working days after; asked for the earliest, the first three working days with an
opening from tomorrow (windows_around). The mock's diary is full on Thursday
mornings and all day on Fridays, so the "not free" paths can be tried on any day.

Fixtures:
- John Smith, 201-555-0123: a visit tomorrow 9 to noon, for the leak under the sink
- Jane Doe, 212-555-0178: no visits
- Maria Garcia, 512-555-0144: two visits, tomorrow 9 to noon (the dripping shower) and the
  first Friday after that, 1 to 4 (the outside light); no account number on file
- Alex Chen, 312-555-0166: a visit about six hours from now (inside the fee window at any hour)
- 201-555-0199: no account
"""

import re
import uuid
from datetime import date, datetime, timedelta

from _gen import *  # <AUTO GENERATED>

LIVE_ENVS = ("pre-release", "pre_release", "live")

SERVICE_TYPES = [
    "General Service",
    "Deep Clean",
    "Emergency Repair",
    "Maintenance Check",
]

# Arrival windows the dispatch system offers each working day (Mon-Sat).
WINDOWS = [("09:00", "12:00"), ("13:00", "16:00")]
SEARCH_DAYS = 14  # how far ahead a lookup goes before the scheduling-team handoff
AROUND_DAYS = 3  # working days either side of the day asked for
# The mock diary's full windows, by weekday (Monday = 0): Thursday mornings and all of Friday.
MOCK_FULL = {3: {"09:00"}, 4: {"09:00", "13:00"}}


@func_description("[UTIL] Dispatch API client, not callable directly")
def api_client(conv: Conversation):
    return "Dispatch API client module."


# --- Mock or real ---------------------------------------------------------


def use_mock_api(conv) -> bool:
    if (conv.env or "").lower() not in LIVE_ENVS:
        return True
    return bool(
        (conv.real_time_config or {}).get("settings", {}).get("use_mock_api", True)
    )


def _real_api_missing(name: str):
    raise NotImplementedError(
        f"{name}: connect your dispatch API here, or keep settings.use_mock_api on"
    )


# --- Seed data --------------------------------------------------------------


def _today(conv=None) -> date:
    try:
        return date.fromisoformat(conv.state.today_iso)
    except (AttributeError, TypeError, ValueError):
        return date.today()


def _customers() -> list[dict]:
    return [
        {
            "id": "MOCK-C001",
            "first_name": "John",
            "last_name": "Smith",
            "phone": "2015550123",
            "address": "123 Main St",
            "zip": "12345",
            "account_number": "48120931",
        },
        {
            "id": "MOCK-C002",
            "first_name": "Jane",
            "last_name": "Doe",
            "phone": "2125550178",
            "address": "456 Oak Ave",
            "zip": "12345",
            "account_number": "48120977",
        },
        {
            "id": "MOCK-C004",
            "first_name": "Alex",
            "last_name": "Chen",
            "phone": "3125550166",
            "address": "12 Pine Rd",
            "zip": "12345",
            "account_number": "48120955",
        },
        {
            "id": "MOCK-C003",
            "first_name": "Maria",
            "last_name": "Garcia",
            "phone": "5125550144",
            "address": "789 Elm St",
            "zip": "12345",
            "account_number": "",
        },
    ]


def _next_weekday(start: date, weekday: int) -> date:
    """The first day on or after `start` that falls on `weekday` (Monday = 0)."""
    return start + timedelta(days=(weekday - start.weekday()) % 7)


def _soon(conv) -> tuple[str, str, str]:
    """Alex Chen's visit: about six hours from now, on the hour, so the cancellation fee
    window can be tried at any time of day."""
    now = getattr(getattr(conv, "state", None), "datetime_now", None)
    if not isinstance(now, datetime):
        now = datetime.combine(_today(conv), datetime.min.time()).replace(hour=12)
    start = (now + timedelta(hours=6)).replace(minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=3)
    return start.date().isoformat(), start.strftime("%H:%M"), end.strftime("%H:%M")


def _seed_appointments(conv=None) -> list[dict]:
    tomorrow = _today(conv) + timedelta(days=1)
    soon_date, soon_start, soon_end = _soon(conv)
    # Maria's second visit: the first Friday after tomorrow.
    friday = _next_weekday(tomorrow + timedelta(days=1), 4)
    visit = {"service_type": "General Service", "location": "", "status": "Scheduled"}
    return [
        {
            **visit,
            "id": "MOCK-APT-001",
            "customer_id": "MOCK-C001",
            "issue": "the leak under your sink",
            "indoor": True,
            "date": tomorrow.isoformat(),
            "start": "09:00",
            "end": "12:00",
        },
        {
            **visit,
            "id": "MOCK-APT-002",
            "customer_id": "MOCK-C003",
            "issue": "the dripping shower",
            "indoor": True,
            "date": tomorrow.isoformat(),
            "start": "09:00",
            "end": "12:00",
        },
        {
            **visit,
            "id": "MOCK-APT-004",
            "customer_id": "MOCK-C004",
            "issue": "the blocked drain",
            "indoor": True,
            "date": soon_date,
            "start": soon_start,
            "end": soon_end,
        },
        {
            **visit,
            "id": "MOCK-APT-003",
            "customer_id": "MOCK-C003",
            "issue": "the outside light",
            "indoor": False,
            "date": friday.isoformat(),
            "start": "13:00",
            "end": "16:00",
        },
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


# --- Customers --------------------------------------------------------------


def find_customers_by_phone(conv, phone: str) -> list[dict]:
    """Every account on this phone number (an empty list when there is none)."""
    if not use_mock_api(conv):
        _real_api_missing("find_customers_by_phone")
    digits = _normalise_phone(phone)
    return [dict(c) for c in _customers() if c["phone"] == digits]


def get_customer(conv, customer_id: str) -> dict | None:
    if not use_mock_api(conv):
        _real_api_missing("get_customer")
    return next((dict(c) for c in _customers() if c["id"] == customer_id), None)


def service_types(conv) -> list[str]:
    if not use_mock_api(conv):
        _real_api_missing("service_types")
    return list(SERVICE_TYPES)


# --- Appointments -----------------------------------------------------------


def list_appointments(conv, customer_id: str) -> list[dict]:
    """Upcoming appointments for a customer, soonest first."""
    if not use_mock_api(conv):
        _real_api_missing("list_appointments")
    changes = _changes(conv)
    appointments = []
    for appt in _seed_appointments(conv) + [dict(a) for a in changes["created"]]:
        if appt["customer_id"] != customer_id or appt["id"] in changes["cancelled"]:
            continue
        appt = {**appt, **changes["moved"].get(appt["id"], {})}
        appointments.append(appt)
    return sorted(appointments, key=lambda a: (a["date"], a["start"]))


def is_working_day(day: date) -> bool:
    return day.weekday() != 6  # technicians don't go out on Sundays


def open_windows(conv, start: date, days: int = SEARCH_DAYS) -> list[dict]:
    """Open arrival windows from `start` for `days` days, soonest first. In the mock a window
    is full when the diary is (MOCK_FULL) or this call has already booked it."""
    if not use_mock_api(conv):
        _real_api_missing("open_windows")
    changes = _changes(conv)
    taken = {(a["date"], a["start"]) for a in changes["created"]}
    taken |= {(m["date"], m["start"]) for m in changes["moved"].values()}
    windows = []
    for offset in range(days):
        day = start + timedelta(days=offset)
        if not is_working_day(day):
            continue
        for begin, end in WINDOWS:
            if (
                begin in MOCK_FULL.get(day.weekday(), set())
                or (day.isoformat(), begin) in taken
            ):
                continue
            windows.append({"date": day.isoformat(), "start": begin, "end": end})
    return windows


def _working_days(start: date, count: int, step: int) -> list[date]:
    days, day = [], start
    while len(days) < count:
        day += timedelta(days=step)
        if is_working_day(day):
            days.append(day)
    return days


def windows_around(conv, wanted: date | None) -> list[dict]:
    """Every open arrival window around a requested day, as the dispatch API returns them.

    wanted None (the earliest): the windows on the first AROUND_DAYS working days with an
    opening, from tomorrow. A day: its windows and those up to AROUND_DAYS working days either
    side, never before tomorrow. Nothing open in that range: the nearest open day after it.
    Nothing within SEARCH_DAYS of tomorrow: an empty list."""
    first = _today(conv) + timedelta(days=1)
    horizon = first + timedelta(days=SEARCH_DAYS)
    every = [
        w
        for w in open_windows(conv, first, SEARCH_DAYS)
        if date.fromisoformat(w["date"]) < horizon
    ]
    if wanted is None:
        days = sorted({w["date"] for w in every})[:AROUND_DAYS]
        return [w for w in every if w["date"] in days]
    wanted = max(wanted, first)
    lo = max(first, (_working_days(wanted, AROUND_DAYS, -1) or [wanted])[-1])
    hi = _working_days(wanted, AROUND_DAYS, 1)[-1]
    inside = [w for w in every if lo.isoformat() <= w["date"] <= hi.isoformat()]
    if inside:
        return inside
    later = [w for w in every if w["date"] > hi.isoformat()]
    return [w for w in later if w["date"] == later[0]["date"]] if later else []


def window_is_open(conv, window: dict) -> bool:
    """Whether a window can still be booked (checked again at write time)."""
    day = date.fromisoformat(window["date"])
    return any(
        w["start"] == window["start"]
        for w in open_windows(conv, day, 1)
        if w["date"] == window["date"]
    )


def _all_live_appointments(conv) -> list[dict]:
    changes = _changes(conv)
    live = []
    for appt in _seed_appointments(conv) + [dict(a) for a in changes["created"]]:
        if appt["id"] in changes["cancelled"]:
            continue
        live.append({**appt, **changes["moved"].get(appt["id"], {})})
    return live


def create_appointment(conv, customer_id: str, window: dict, details: dict) -> dict:
    """Book a window. Returns the new appointment."""
    if not use_mock_api(conv):
        _real_api_missing("create_appointment")
    appt = {
        "id": f"MOCK-APT-{uuid.uuid4().hex[:6].upper()}",
        "customer_id": customer_id,
        "service_type": details.get("service_type") or "General Service",
        "issue": details.get("issue") or "",
        "location": details.get("location") or "",
        "indoor": bool(details.get("indoor")),
        "date": window["date"],
        "start": window["start"],
        "end": window["end"],
        "status": "Scheduled",
    }
    changes = _changes(conv)
    changes["created"] = changes["created"] + [appt]
    conv.state.mock_changes = changes
    return dict(appt)


def move_appointment(conv, appointment_id: str, window: dict) -> bool:
    if not use_mock_api(conv):
        _real_api_missing("move_appointment")
    changes = _changes(conv)
    moved = dict(changes["moved"])
    moved[appointment_id] = {
        "date": window["date"],
        "start": window["start"],
        "end": window["end"],
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
