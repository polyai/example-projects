"""
Mock API for field service scheduling template.

Provides in-memory test customers, appointments, and available slots
for local development and testing when no real dispatch system backend
is available.
"""

import copy
import re
import uuid
from datetime import datetime, timedelta
from typing import Optional

from _gen import *  # <AUTO GENERATED>


def _normalize_phone(phone: str) -> str:
    """Strip formatting and leading US country code '1' from a phone number."""
    cleaned = re.sub(r"[\s()+-]", "", phone or "")
    if len(cleaned) == 11 and cleaned.startswith("1"):
        cleaned = cleaned[1:]
    return cleaned


def _today() -> datetime:
    """Return today at midnight (no time component)."""
    return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)


# ---------------------------------------------------------------------------
# Seed data builders (called at import time and by reset_mock_data)
# ---------------------------------------------------------------------------

SERVICE_TYPES = [
    {"typeID": "ST-001", "description": "General Service", "visible": "1"},
    {"typeID": "ST-002", "description": "Deep Clean", "visible": "1"},
    {"typeID": "ST-003", "description": "Emergency Repair", "visible": "1"},
    {"typeID": "ST-004", "description": "Maintenance Check", "visible": "1"},
]


def _build_customers() -> dict[str, dict]:
    return {
        "MOCK-C001": {
            "customerID": "MOCK-C001",
            "fname": "John",
            "lname": "Smith",
            "phone": "5550001234",
            "address": "123 Main St",
            "city": "Anytown",
            "state": "US",
            "zip": "12345",
            "lat": "40.7128",
            "lng": "-74.0060",
            "officeID": "10",
            "subscriptionIDs": "SUB-001",
        },
        "MOCK-C002": {
            "customerID": "MOCK-C002",
            "fname": "Jane",
            "lname": "Doe",
            "phone": "5550005678",
            "address": "456 Oak Ave",
            "city": "Anytown",
            "state": "US",
            "zip": "12345",
            "lat": "40.7200",
            "lng": "-74.0100",
            "officeID": "10",
            "subscriptionIDs": "SUB-002",
        },
    }


def _build_appointments() -> dict[str, dict]:
    tomorrow = (_today() + timedelta(days=1)).strftime("%Y-%m-%d")
    return {
        "MOCK-APT-001": {
            "appointmentID": "MOCK-APT-001",
            "customerID": "MOCK-C001",
            "routeID": "MOCK-R001",
            "type": "ST-001",
            "date": tomorrow,
            "start": "09:00:00",
            "end": "12:00:00",
            "statusText": "Scheduled",
            "doInterior": 0,
            "serviceTypes": "",
            "notes": "Mock appointment",
            "spotID": "MOCK-SPOT-001",
        },
    }


def _build_available_slots() -> list[dict]:
    """Build available slots relative to today."""
    tomorrow = (_today() + timedelta(days=1)).strftime("%Y-%m-%d")
    day_after = (_today() + timedelta(days=2)).strftime("%Y-%m-%d")
    three_days = (_today() + timedelta(days=3)).strftime("%Y-%m-%d")
    return [
        {
            "date": tomorrow,
            "time_window": "1pm-4pm",
            "start": "13:00:00",
            "end": "16:00:00",
            "spotID": "MOCK-SPOT-010",
        },
        {
            "date": day_after,
            "time_window": "9am-12pm",
            "start": "09:00:00",
            "end": "12:00:00",
            "spotID": "MOCK-SPOT-011",
        },
        {
            "date": day_after,
            "time_window": "1pm-4pm",
            "start": "13:00:00",
            "end": "16:00:00",
            "spotID": "MOCK-SPOT-012",
        },
        {
            "date": three_days,
            "time_window": "9am-12pm",
            "start": "09:00:00",
            "end": "12:00:00",
            "spotID": "MOCK-SPOT-013",
        },
    ]


# ---------------------------------------------------------------------------
# Module-level state (mutable, reset between tests)
# ---------------------------------------------------------------------------

_CUSTOMERS: dict[str, dict] = _build_customers()
_PHONE_INDEX: dict[str, str] = {c["phone"]: cid for cid, c in _CUSTOMERS.items()}
_APPOINTMENTS: dict[str, dict] = _build_appointments()
_AVAILABLE_SLOTS: list[dict] = _build_available_slots()


# ---------------------------------------------------------------------------
# MockDispatchApi
# ---------------------------------------------------------------------------


class MockDispatchApi:
    """In-memory dispatch/scheduling operations for testing."""

    # -- Customer lookup ----------------------------------------------------

    @staticmethod
    def lookup_customer_by_phone(phone: str) -> Optional[dict]:
        """Look up a customer by phone number. Returns customer dict or None."""
        cleaned = _normalize_phone(phone)
        customer_id = _PHONE_INDEX.get(cleaned)
        if customer_id is None:
            return None
        return copy.deepcopy(_CUSTOMERS[customer_id])

    # -- Appointments -------------------------------------------------------

    @staticmethod
    def get_appointments(customer_id: str) -> list[dict]:
        """Return all appointments for a given customer ID."""
        return [
            copy.deepcopy(apt) for apt in _APPOINTMENTS.values() if apt["customerID"] == customer_id
        ]

    # -- Available slots ----------------------------------------------------

    @staticmethod
    def get_available_slots(
        date: Optional[str] = None, service_type: Optional[str] = None
    ) -> list[dict]:
        """
        Return available slots, optionally filtered by date and/or service type.

        All service types share the same slot availability in this mock.
        """
        slots = _AVAILABLE_SLOTS
        if date is not None:
            slots = [s for s in slots if s["date"] == date]
        # service_type filtering is a no-op in the mock (all types share slots)
        # but we accept the parameter to match the real API interface.
        return [copy.deepcopy(s) for s in slots]

    # -- Create appointment -------------------------------------------------

    @staticmethod
    def create_appointment(
        customer_id: str,
        date: str,
        time_window: str,
        service_type: str,
        notes: str = "",
    ) -> Optional[dict]:
        """
        Create a new appointment. Returns the appointment dict or None if
        the customer doesn't exist.
        """
        if customer_id not in _CUSTOMERS:
            return None

        # Resolve time_window to start/end
        start, end = _resolve_time_window(time_window)

        # Resolve service type ID
        type_id = _resolve_service_type(service_type)

        appointment_id = f"MOCK-APT-{uuid.uuid4().hex[:6].upper()}"
        appointment = {
            "appointmentID": appointment_id,
            "customerID": customer_id,
            "routeID": f"MOCK-R-{uuid.uuid4().hex[:4].upper()}",
            "type": type_id,
            "date": date,
            "start": start,
            "end": end,
            "statusText": "Scheduled",
            "doInterior": 0,
            "serviceTypes": "",
            "notes": notes,
            "spotID": f"MOCK-SPOT-{uuid.uuid4().hex[:4].upper()}",
        }
        _APPOINTMENTS[appointment_id] = appointment
        return copy.deepcopy(appointment)

    # -- Cancel appointment -------------------------------------------------

    @staticmethod
    def cancel_appointment(appointment_id: str, reason: str = "") -> dict:
        """
        Cancel an appointment by ID.

        Returns {"success": True} if found and cancelled,
        {"success": False, "error": "..."} otherwise.
        """
        if appointment_id not in _APPOINTMENTS:
            return {"success": False, "error": f"Appointment {appointment_id} not found"}
        del _APPOINTMENTS[appointment_id]
        return {"success": True, "reason": reason}

    # -- Reschedule appointment ---------------------------------------------

    @staticmethod
    def reschedule_appointment(
        appointment_id: str,
        new_date: str,
        new_time_window: str,
    ) -> Optional[dict]:
        """
        Reschedule an existing appointment. Returns updated appointment dict
        or None if the appointment doesn't exist.
        """
        if appointment_id not in _APPOINTMENTS:
            return None

        start, end = _resolve_time_window(new_time_window)
        _APPOINTMENTS[appointment_id]["date"] = new_date
        _APPOINTMENTS[appointment_id]["start"] = start
        _APPOINTMENTS[appointment_id]["end"] = end
        return copy.deepcopy(_APPOINTMENTS[appointment_id])


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_TIME_WINDOW_MAP = {
    "9am-12pm": ("09:00:00", "12:00:00"),
    "1pm-4pm": ("13:00:00", "16:00:00"),
    "8am-12pm": ("08:00:00", "12:00:00"),
    "12pm-4pm": ("12:00:00", "16:00:00"),
}


def _resolve_time_window(time_window: str) -> tuple[str, str]:
    """Convert a human-readable time window to (start, end) HH:MM:SS strings."""
    if time_window in _TIME_WINDOW_MAP:
        return _TIME_WINDOW_MAP[time_window]
    # Fallback: default to full-day window
    return ("08:00:00", "20:00:00")


def _resolve_service_type(service_type: str) -> str:
    """Map a service type description to its typeID."""
    for st in SERVICE_TYPES:
        if st["description"].lower() == service_type.lower():
            return st["typeID"]
    # Default to General Service if not found
    return "ST-001"


# ---------------------------------------------------------------------------
# Reset helper (for tests)
# ---------------------------------------------------------------------------


def reset_mock_data() -> None:
    """Restore all mock data to its original state."""
    global _CUSTOMERS, _PHONE_INDEX, _APPOINTMENTS, _AVAILABLE_SLOTS
    _CUSTOMERS.clear()
    _CUSTOMERS.update(_build_customers())
    _PHONE_INDEX.clear()
    _PHONE_INDEX.update({c["phone"]: cid for cid, c in _CUSTOMERS.items()})
    _APPOINTMENTS.clear()
    _APPOINTMENTS.update(_build_appointments())
    _AVAILABLE_SLOTS.clear()
    _AVAILABLE_SLOTS.extend(_build_available_slots())


@func_description("[UTIL] Mock dispatch/scheduling API for testing")
def mock_api(conv: Conversation):
    pass
