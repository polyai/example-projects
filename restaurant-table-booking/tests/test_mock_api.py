"""Tests for the mock OpenTable API — verifies the in-memory reservation system."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest
from functions.mock_api import MockOpenTableApi


def _tomorrow_7pm():
    dt = datetime.now().replace(hour=19, minute=0, second=0, microsecond=0) + timedelta(days=1)
    return dt.strftime("%Y-%m-%dT%H:%M")


@pytest.fixture
def api():
    conv = MagicMock()
    return MockOpenTableApi(conv)


def _json(response):
    """Extract JSON from response — handles both raw dicts and _MockResponse objects."""
    if isinstance(response, dict):
        return response
    if isinstance(response, list):
        return response
    return response.json()


class TestAvailability:
    def test_returns_slots_for_valid_party(self, api):
        result = _json(api.check_availability(party_size=4, date_time=_tomorrow_7pm()))
        assert "times_available" in result
        assert len(result["times_available"]) > 0

    def test_returns_empty_for_no_match(self, api):
        result = _json(api.check_availability(party_size=4, date_time="2099-12-31T03:00"))
        assert len(result.get("times_available", [])) == 0


class TestBookingFlow:
    def test_lock_returns_token(self, api):
        result = _json(api.lock_booking(party_size=4, date_time=_tomorrow_7pm()))
        assert "reservation_token" in result

    def test_finalize_creates_booking(self, api):
        lock = _json(api.lock_booking(party_size=2, date_time=_tomorrow_7pm()))
        token = lock["reservation_token"]

        result = _json(
            api.finalize_booking(
                first_name="Test",
                last_name="User",
                phone_number="5559999999",
                country_code=1,
                reservation_token=token,
            )
        )
        assert result["first_name"] == "Test"
        assert result["party_size"] == 2


class TestCancelBooking:
    def test_cancel_existing(self, api):
        resp = api.cancel_booking("mock-booking-001")
        ok = (hasattr(resp, "ok") and resp.ok) or (
            hasattr(resp, "status_code") and resp.status_code == 200
        )
        assert ok

    def test_cancel_nonexistent(self, api):
        result = _json(api.cancel_booking("NONEXISTENT"))
        assert result.get("errors") or result.get("status") != "cancelled"


class TestModifyBooking:
    def test_modify_party_size(self, api):
        resp = api.modify_booking("mock-booking-002", party_size=6)
        ok = (hasattr(resp, "ok") and resp.ok) or (
            hasattr(resp, "status_code") and resp.status_code == 200
        )
        assert ok
        result = _json(resp)
        assert result.get("party_size") == 6 or result.get("reservation", {}).get("party_size") == 6


class TestGuestSearch:
    def test_known_guest(self, api):
        result = api.guest_search("5550001234")
        if not isinstance(result, dict):
            result = result.json() if hasattr(result, "json") else result
        assert result["count"] >= 1
        assert result["candidates"][0]["firstName"] == "John"

    def test_unknown_guest(self, api):
        result = api.guest_search("0000000000")
        if not isinstance(result, dict):
            result = result.json() if hasattr(result, "json") else result
        assert result["count"] == 0


class TestGetBookings:
    def test_known_phone(self, api):
        result = api.get_bookings("5550005678")
        bookings = result.json() if hasattr(result, "json") else result
        if isinstance(bookings, dict):
            bookings = bookings.get("reservations", [])
        assert len(bookings) >= 1

    def test_unknown_phone(self, api):
        result = api.get_bookings("0000000000")
        bookings = result.json() if hasattr(result, "json") else result
        if isinstance(bookings, dict):
            bookings = bookings.get("reservations", [])
        assert len(bookings) == 0
