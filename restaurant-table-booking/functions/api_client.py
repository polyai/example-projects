"""Reservation API client: guests, bookings and open tables.

Every tool reads and writes through this module, so connecting a real reservation
system means replacing the bodies of the helpers below and nothing else.

Mock or real (see use_mock_api):
- branch, draft and sandbox always use the mock, so a test call never touches a
  real system;
- pre-release and live use the mock until the real API is connected and
  `settings.use_mock_api` is set to false in real-time config.

The mock keeps every change a call makes (new bookings, changes, cancellations)
in conv.state, so two test calls never see each other's bookings. The seed data
is rebuilt from the functions below on every read and never mutated.

Fixtures (dates are relative to the day of the call):
- John Smith, 201-555-0123: table for 4 tomorrow at 7pm
- Jane Doe, 212-555-0178: table for 2 the day after tomorrow at 8pm
- Maria Garcia, 312-555-0144: table for 2 in two days at 6pm, and for 6 in four days at 7:30pm
- Alex Turner, 201-555-0177: guest with no upcoming bookings
- 201-555-0199: no guest on file
"""

import re
import uuid
from datetime import date, timedelta

from _gen import *  # <AUTO GENERATED>

LIVE_ENVS = ("pre-release", "pre_release", "live")

# Mock floor plan: the times a table can start, and how many covers (seats) the
# room takes at each of them. Opening hours are applied by bookings.py.
SLOT_TIMES = [
    "12:00", "12:30", "13:00", "13:30",
    "17:30", "18:00", "18:30", "19:00", "19:30", "20:00", "20:30",
]  # fmt: skip
COVERS_PER_SLOT = 10


@func_description("[UTIL] Reservation API client, not callable directly")
def api_client(conv: Conversation):
    return "Reservation API client module."


# --- Mock or real ---------------------------------------------------------


def use_mock_api(conv) -> bool:
    if (conv.env or "").lower() not in LIVE_ENVS:
        return True
    return bool(
        (conv.real_time_config or {}).get("settings", {}).get("use_mock_api", True)
    )


def _real_api_missing(name: str):
    raise NotImplementedError(
        f"{name}: connect your reservation API here, or keep settings.use_mock_api on"
    )


# --- Seed data --------------------------------------------------------------


def _today(conv=None) -> date:
    try:
        return date.fromisoformat(conv.state.today_iso)
    except (AttributeError, TypeError, ValueError):
        return date.today()


def _guests() -> list[dict]:
    return [
        {
            "id": "G-001",
            "first_name": "John",
            "last_name": "Smith",
            "phone": "2015550123",
        },
        {
            "id": "G-002",
            "first_name": "Jane",
            "last_name": "Doe",
            "phone": "2125550178",
        },
        {
            "id": "G-003",
            "first_name": "Maria",
            "last_name": "Garcia",
            "phone": "3125550144",
        },
        {
            "id": "G-004",
            "first_name": "Alex",
            "last_name": "Turner",
            "phone": "2015550177",
        },
    ]


def _seed_bookings(conv=None) -> list[dict]:
    today = _today(conv)
    guests = {g["id"]: g for g in _guests()}

    def booking(bid, guest_id, days, time, party):
        guest = guests[guest_id]
        return {
            "id": bid,
            "guest_id": guest_id,
            "first_name": guest["first_name"],
            "last_name": guest["last_name"],
            "phone": guest["phone"],
            "date": (today + timedelta(days=days)).isoformat(),
            "time": time,
            "party_size": party,
            "notes": "",
        }

    return [
        booking("MOCK-BKG-001", "G-001", 1, "19:00", 4),
        booking("MOCK-BKG-002", "G-002", 2, "20:00", 2),
        booking("MOCK-BKG-003", "G-003", 2, "18:00", 2),
        booking("MOCK-BKG-004", "G-003", 4, "19:30", 6),
        booking("MOCK-BKG-005", "G-004", -3, "19:00", 2),  # in the past
    ]


def _changes(conv) -> dict:
    """This call's new guests, bookings, changes and cancellations, kept in conv.state."""
    changes = conv.state.mock_changes
    if not isinstance(changes, dict):
        changes = {"guests": [], "created": [], "updated": {}, "cancelled": []}
        conv.state.mock_changes = changes
    return changes


def _save(conv, changes: dict) -> None:
    conv.state.mock_changes = changes


def _normalise_phone(value) -> str:
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits


def _all_bookings(conv) -> list[dict]:
    changes = _changes(conv)
    live = []
    for b in _seed_bookings(conv) + [dict(x) for x in changes["created"]]:
        if b["id"] in changes["cancelled"]:
            continue
        live.append({**b, **changes["updated"].get(b["id"], {})})
    return live


# --- Guests -----------------------------------------------------------------


def find_guests_by_phone(conv, phone: str) -> list[dict]:
    """Every guest on file with this phone number (an empty list when there is none)."""
    if not use_mock_api(conv):
        _real_api_missing("find_guests_by_phone")
    digits = _normalise_phone(phone)
    guests = _guests() + [dict(g) for g in _changes(conv)["guests"]]
    return [dict(g) for g in guests if g["phone"] == digits]


def _guest_for(conv, first_name: str, last_name: str, phone: str) -> dict:
    """The guest on this phone with this name, added for the call if new."""
    wanted = (first_name.strip().lower(), last_name.strip().lower())
    for g in find_guests_by_phone(conv, phone):
        if (g["first_name"].lower(), g["last_name"].lower()) == wanted:
            return g
    guest = {
        "id": f"G-{uuid.uuid4().hex[:6].upper()}",
        "first_name": first_name.strip(),
        "last_name": last_name.strip(),
        "phone": _normalise_phone(phone),
    }
    changes = _changes(conv)
    changes["guests"] = changes["guests"] + [guest]
    _save(conv, changes)
    return dict(guest)


# --- Bookings ---------------------------------------------------------------


def list_bookings(conv, guest_id: str) -> list[dict]:
    """A guest's upcoming bookings (today onwards), soonest first."""
    if not use_mock_api(conv):
        _real_api_missing("list_bookings")
    today = _today(conv).isoformat()
    upcoming = [
        b
        for b in _all_bookings(conv)
        if b["guest_id"] == guest_id and b["date"] >= today
    ]
    return sorted(upcoming, key=lambda b: (b["date"], b["time"]))


def get_booking(conv, booking_id: str) -> dict | None:
    if not use_mock_api(conv):
        _real_api_missing("get_booking")
    return next((b for b in _all_bookings(conv) if b["id"] == booking_id), None)


def available_times(
    conv, day: date, party_size: int, ignore_booking_id: str = ""
) -> list[str]:
    """Start times on `day` with room for `party_size` ("HH:MM", earliest first).

    ignore_booking_id: a booking being changed, whose own covers don't count
    against the room.
    """
    if not use_mock_api(conv):
        _real_api_missing("available_times")
    taken: dict[str, int] = {}
    for b in _all_bookings(conv):
        if b["date"] == day.isoformat() and b["id"] != ignore_booking_id:
            taken[b["time"]] = taken.get(b["time"], 0) + int(b["party_size"])
    return [
        t for t in SLOT_TIMES if taken.get(t, 0) + int(party_size) <= COVERS_PER_SLOT
    ]


def create_booking(
    conv, guest: dict, day: str, time: str, party_size: int, notes: str = ""
) -> dict:
    """Book a table for `guest` ({first_name, last_name, phone}). Returns the new booking."""
    if not use_mock_api(conv):
        _real_api_missing("create_booking")
    record = _guest_for(conv, guest["first_name"], guest["last_name"], guest["phone"])
    booking = {
        "id": f"MOCK-BKG-{uuid.uuid4().hex[:6].upper()}",
        "guest_id": record["id"],
        "first_name": record["first_name"],
        "last_name": record["last_name"],
        "phone": record["phone"],
        "date": day,
        "time": time,
        "party_size": int(party_size),
        "notes": notes or "",
    }
    changes = _changes(conv)
    changes["created"] = changes["created"] + [booking]
    _save(conv, changes)
    return dict(booking)


def update_booking(conv, booking_id: str, new_values: dict) -> dict | None:
    """Change the date, time, party size or notes of a booking. Returns the booking."""
    if not use_mock_api(conv):
        _real_api_missing("update_booking")
    allowed = {
        k: v
        for k, v in new_values.items()
        if k in ("date", "time", "party_size", "notes")
    }
    changes = _changes(conv)
    updated = dict(changes["updated"])
    updated[booking_id] = {**updated.get(booking_id, {}), **allowed}
    changes["updated"] = updated
    _save(conv, changes)
    return get_booking(conv, booking_id)


def cancel_booking(conv, booking_id: str, reason: str = "") -> bool:
    if not use_mock_api(conv):
        _real_api_missing("cancel_booking")
    changes = _changes(conv)
    changes["cancelled"] = changes["cancelled"] + [booking_id]
    _save(conv, changes)
    conv.log.info("Mock cancellation", booking_id=booking_id, reason=reason)
    return True
