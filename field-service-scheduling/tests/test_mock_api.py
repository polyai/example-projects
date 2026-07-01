"""Tests for the field service scheduling mock API."""

from datetime import datetime, timedelta

import pytest
from functions.mock_api import MockDispatchApi, reset_mock_data

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset():
    """Reset mock data before each test to prevent cross-test pollution."""
    reset_mock_data()


def _tomorrow() -> str:
    return (
        datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    ).strftime("%Y-%m-%d")


def _day_after() -> str:
    return (
        datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=2)
    ).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Customer lookup
# ---------------------------------------------------------------------------


class TestLookupCustomerByPhone:
    def test_known_phone_john(self):
        customer = MockDispatchApi.lookup_customer_by_phone("5550001234")
        assert customer is not None
        assert customer["customerID"] == "MOCK-C001"
        assert customer["fname"] == "John"
        assert customer["lname"] == "Smith"
        assert customer["address"] == "123 Main St"

    def test_known_phone_jane(self):
        customer = MockDispatchApi.lookup_customer_by_phone("5550005678")
        assert customer is not None
        assert customer["customerID"] == "MOCK-C002"
        assert customer["fname"] == "Jane"
        assert customer["lname"] == "Doe"

    def test_unknown_phone_returns_none(self):
        assert MockDispatchApi.lookup_customer_by_phone("0000000000") is None

    def test_phone_with_formatting(self):
        customer = MockDispatchApi.lookup_customer_by_phone("+1 (555) 000-1234")
        assert customer is not None
        assert customer["customerID"] == "MOCK-C001"


# ---------------------------------------------------------------------------
# Get appointments
# ---------------------------------------------------------------------------


class TestGetAppointments:
    def test_customer_with_appointment(self):
        appointments = MockDispatchApi.get_appointments("MOCK-C001")
        assert len(appointments) == 1
        assert appointments[0]["appointmentID"] == "MOCK-APT-001"
        assert appointments[0]["date"] == _tomorrow()
        assert appointments[0]["statusText"] == "Scheduled"

    def test_customer_with_no_appointments(self):
        appointments = MockDispatchApi.get_appointments("MOCK-C002")
        assert appointments == []

    def test_unknown_customer_returns_empty(self):
        appointments = MockDispatchApi.get_appointments("NONEXISTENT")
        assert appointments == []


# ---------------------------------------------------------------------------
# Available slots
# ---------------------------------------------------------------------------


class TestGetAvailableSlots:
    def test_returns_slots_for_tomorrow(self):
        slots = MockDispatchApi.get_available_slots(date=_tomorrow())
        assert len(slots) == 1
        assert slots[0]["time_window"] == "1pm-4pm"

    def test_returns_slots_for_day_after(self):
        slots = MockDispatchApi.get_available_slots(date=_day_after())
        assert len(slots) == 2

    def test_returns_all_slots_when_no_date(self):
        slots = MockDispatchApi.get_available_slots()
        assert len(slots) == 4

    def test_no_slots_for_far_future(self):
        far_future = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        slots = MockDispatchApi.get_available_slots(date=far_future)
        assert slots == []


# ---------------------------------------------------------------------------
# Create appointment
# ---------------------------------------------------------------------------


class TestCreateAppointment:
    def test_create_success(self):
        result = MockDispatchApi.create_appointment(
            customer_id="MOCK-C001",
            date=_tomorrow(),
            time_window="1pm-4pm",
            service_type="General Service",
            notes="Test appointment",
        )
        assert result is not None
        assert result["customerID"] == "MOCK-C001"
        assert result["date"] == _tomorrow()
        assert result["start"] == "13:00:00"
        assert result["end"] == "16:00:00"
        assert result["statusText"] == "Scheduled"
        assert result["notes"] == "Test appointment"

    def test_create_appears_in_get_appointments(self):
        before = MockDispatchApi.get_appointments("MOCK-C002")
        assert len(before) == 0

        MockDispatchApi.create_appointment(
            customer_id="MOCK-C002",
            date=_day_after(),
            time_window="9am-12pm",
            service_type="Deep Clean",
        )
        after = MockDispatchApi.get_appointments("MOCK-C002")
        assert len(after) == 1
        assert after[0]["type"] == "ST-002"

    def test_create_unknown_customer_returns_none(self):
        result = MockDispatchApi.create_appointment(
            customer_id="NONEXISTENT",
            date=_tomorrow(),
            time_window="9am-12pm",
            service_type="General Service",
        )
        assert result is None


# ---------------------------------------------------------------------------
# Cancel appointment
# ---------------------------------------------------------------------------


class TestCancelAppointment:
    def test_cancel_success(self):
        result = MockDispatchApi.cancel_appointment("MOCK-APT-001", reason="No longer needed")
        assert result["success"] is True

    def test_cancel_removes_from_get_appointments(self):
        MockDispatchApi.cancel_appointment("MOCK-APT-001")
        appointments = MockDispatchApi.get_appointments("MOCK-C001")
        assert len(appointments) == 0

    def test_cancel_nonexistent_returns_failure(self):
        result = MockDispatchApi.cancel_appointment("NONEXISTENT")
        assert result["success"] is False
        assert "error" in result


# ---------------------------------------------------------------------------
# Reschedule appointment
# ---------------------------------------------------------------------------


class TestRescheduleAppointment:
    def test_reschedule_success(self):
        result = MockDispatchApi.reschedule_appointment(
            appointment_id="MOCK-APT-001",
            new_date=_day_after(),
            new_time_window="1pm-4pm",
        )
        assert result is not None
        assert result["date"] == _day_after()
        assert result["start"] == "13:00:00"
        assert result["end"] == "16:00:00"

    def test_reschedule_updates_get_appointments(self):
        MockDispatchApi.reschedule_appointment(
            appointment_id="MOCK-APT-001",
            new_date=_day_after(),
            new_time_window="9am-12pm",
        )
        appointments = MockDispatchApi.get_appointments("MOCK-C001")
        assert len(appointments) == 1
        assert appointments[0]["date"] == _day_after()
        assert appointments[0]["start"] == "09:00:00"

    def test_reschedule_nonexistent_returns_none(self):
        result = MockDispatchApi.reschedule_appointment(
            appointment_id="NONEXISTENT",
            new_date=_tomorrow(),
            new_time_window="9am-12pm",
        )
        assert result is None
