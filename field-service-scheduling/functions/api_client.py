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

Fixtures:
- John Smith, 201-555-0123, ZIP 12345: General Service visit tomorrow 9am-12pm
- Jane Doe, 212-555-0178, ZIP 12345: no visits
- 201-555-0199: no account
"""

import re
import uuid
from datetime import date, timedelta

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
SEARCH_DAYS = 14


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
    ]


def _seed_appointments(conv=None) -> list[dict]:
    tomorrow = _today(conv) + timedelta(days=1)
    return [
        {
            "id": "MOCK-APT-001",
            "customer_id": "MOCK-C001",
            "service_type": "General Service",
            "issue": "",
            "location": "",
            "indoor": False,
            "date": tomorrow.isoformat(),
            "start": "09:00",
            "end": "12:00",
            "status": "Scheduled",
        }
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


def open_windows(conv, start: date, days: int = SEARCH_DAYS) -> list[dict]:
    """Open arrival windows from `start` for `days` days, soonest first."""
    if not use_mock_api(conv):
        _real_api_missing("open_windows")
    taken = set()
    for appt in _all_live_appointments(conv):
        taken.add((appt["date"], appt["start"]))
    windows = []
    for offset in range(days):
        day = start + timedelta(days=offset)
        if day.weekday() == 6:  # closed on Sundays
            continue
        for begin, end in WINDOWS:
            if (day.isoformat(), begin) in taken:
                continue
            windows.append({"date": day.isoformat(), "start": begin, "end": end})
    return windows


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
