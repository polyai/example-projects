"""Tests for the mock API handler — verifies the in-memory EHR mock works correctly."""

from unittest.mock import MagicMock

import pytest
from functions.mock_api import MockApiHandler
from functions.nextgen_request_models import AppointmentCreateRequest, AppointmentRescheduleRequest
from functions.nextgen_response_models import Appointment, AppointmentSlot, Person


@pytest.fixture
def mock_conv():
    conv = MagicMock()
    conv.log = MagicMock()
    return conv


@pytest.fixture
def handler(mock_conv):
    return MockApiHandler(mock_conv)


class TestPatientLookup:
    """Golden path: verify a test patient by phone and DOB."""

    def test_lookup_by_phone_returns_patient(self, handler):
        results = handler.lookup_patients("5550001234")
        assert len(results) == 1
        assert isinstance(results[0], Person)
        assert results[0].first_name == "Jane"
        assert results[0].last_name == "Smith"

    def test_lookup_by_phone_and_dob(self, handler):
        results = handler.lookup_patients("5550001234", date_of_birth="1985-03-15")
        assert len(results) == 1
        assert results[0].id == "MOCK-P001"

    def test_lookup_wrong_dob_returns_empty(self, handler):
        results = handler.lookup_patients("5550001234", date_of_birth="1999-01-01")
        assert len(results) == 0

    def test_lookup_unknown_phone_returns_empty(self, handler):
        results = handler.lookup_patients("0000000000")
        assert len(results) == 0

    def test_get_person_by_id(self, handler):
        person = handler.get_person("MOCK-P001")
        assert person is not None
        assert person.first_name == "Jane"

    def test_get_person_unknown_id(self, handler):
        person = handler.get_person("NONEXISTENT")
        assert person is None


class TestAppointmentBooking:
    """Golden path: search slots, create an appointment."""

    def test_search_slots_returns_results(self, handler):
        slots = handler.search_appointment_slots("2025-08-20")
        assert len(slots) > 0
        assert all(isinstance(s, AppointmentSlot) for s in slots)

    def test_create_appointment(self, handler):
        payload = AppointmentCreateRequest(
            PersonId="MOCK-P001",
            EventId="MOCK-E001",
            LocationId="MOCK-L001",
            ResourceIds=["MOCK-R001"],
            AppointmentDate="2025-08-20T09:00:00",
            DurationMinutes=30,
        )
        result = handler.create_appointment(payload)
        assert result is not None
        assert isinstance(result, Appointment)

        appts = handler.get_person_appointments("MOCK-P001")
        new_appt = [a for a in appts if a.appointment_date == "2025-08-20T09:00:00"]
        assert len(new_appt) == 1


class TestAppointmentCancellation:
    """Edge case: cancel an appointment, verify it's marked cancelled."""

    def test_cancel_existing_appointment(self, handler):
        appts = handler.get_person_appointments("MOCK-P001")
        assert len(appts) > 0

        appt_id = appts[0].id or appts[0].appointment_id
        result = handler.cancel_appointment(appt_id, "MOCK-CANCEL-REASON")
        assert result is not None
        assert result.is_cancelled is True

    def test_cancel_nonexistent_appointment(self, handler):
        result = handler.cancel_appointment("NONEXISTENT", "MOCK-CANCEL-REASON")
        assert result is None


class TestAppointmentReschedule:
    """Reschedule flow: verify old appointment is marked rescheduled."""

    def test_reschedule_appointment(self, handler):
        appts = handler.get_person_appointments("MOCK-P002")
        original = appts[0]
        original_id = original.id or original.appointment_id

        payload = AppointmentRescheduleRequest(
            AppointmentDate="2025-08-21T10:00:00",
            DurationMinutes=30,
        )
        result = handler.reschedule_appointment(original_id, payload)
        assert result is not None
        assert isinstance(result, Appointment)

        updated_appts = handler.get_person_appointments("MOCK-P002")
        originals = [a for a in updated_appts if (a.id or a.appointment_id) == original_id]
        if originals:
            assert originals[0].is_rescheduled is True


class TestInsuranceAndResources:
    """Failure path: insurance lookup for unknown patient."""

    def test_get_insurances_for_known_patient(self, handler):
        insurances = handler.get_person_insurances("MOCK-P001")
        assert len(insurances) > 0
        assert insurances[0].payer_name is not None

    def test_get_insurances_unknown_patient(self, handler):
        insurances = handler.get_person_insurances("NONEXISTENT")
        assert len(insurances) == 0

    def test_list_resources(self, handler):
        resources = handler.list_resources()
        assert len(resources) >= 2

    def test_ensure_session_id(self, handler):
        session_id = handler.ensure_session_id()
        assert session_id == "MOCK-SESSION"
