import copy
import uuid
from datetime import UTC, datetime, timedelta
from typing import Optional

from _gen import *  # <AUTO GENERATED>

from .nextgen_request_models import (
    AppointmentAvailabilityRequest,
    AppointmentCreateRequest,
    AppointmentRescheduleRequest,
    PersonCreateRequest,
)
from .nextgen_response_models import (
    Appointment,
    AppointmentSlot,
    ListItem,
    Person,
    PersonInsurance,
    Resource,
)


def _mock_id() -> str:
    return f"MOCK-{uuid.uuid4().hex[:8].upper()}"


def _future_date(days_ahead: int, hour: int = 9, minute: int = 0) -> str:
    dt = datetime.now(UTC) + timedelta(days=days_ahead)
    return dt.replace(hour=hour, minute=minute, second=0, microsecond=0).strftime(
        "%Y-%m-%dT%H:%M:%S"
    )


# ---------------------------------------------------------------------------
# In-memory mock database -- seeded with deterministic test data
# ---------------------------------------------------------------------------

_PERSONS: dict[str, dict] = {
    "MOCK-P001": {
        "id": "MOCK-P001",
        "firstName": "Jane",
        "lastName": "Smith",
        "dateOfBirth": "1985-03-15",
        "sex": "Female",
        "homePhone": "5550001234",
        "cellPhone": "5550001234",
        "isPatient": True,
        "primaryCareProviderId": "MOCK-R001",
    },
    "MOCK-P002": {
        "id": "MOCK-P002",
        "firstName": "John",
        "lastName": "Doe",
        "dateOfBirth": "1990-07-22",
        "sex": "Male",
        "homePhone": "5550005678",
        "cellPhone": "5550005678",
        "isPatient": True,
        "primaryCareProviderId": "MOCK-R002",
    },
}

# Map phone number -> list of person IDs for lookup
_PHONE_INDEX: dict[str, list[str]] = {
    "5550001234": ["MOCK-P001"],
    "5550005678": ["MOCK-P002"],
}

_APPOINTMENTS: dict[str, dict] = {
    "MOCK-A001": {
        "appointmentId": "MOCK-A001",
        "id": "MOCK-A001",
        "personId": "MOCK-P001",
        "eventId": "b5c6d1f8-1820-4c47-ad1a-d6e5e61c8d90",
        "resourceId": "MOCK-R001",
        "appointmentDate": _future_date(5, 10, 0),
        "isCancelled": False,
        "isRescheduled": False,
        "isKept": False,
        "details": "Recheck",
    },
    "MOCK-A002": {
        "appointmentId": "MOCK-A002",
        "id": "MOCK-A002",
        "personId": "MOCK-P002",
        "eventId": "b5c6d1f8-1820-4c47-ad1a-d6e5e61c8d90",
        "resourceId": "MOCK-R001",
        "appointmentDate": _future_date(7, 9, 0),
        "isCancelled": False,
        "isRescheduled": False,
        "isKept": False,
        "details": "Recheck",
    },
    "MOCK-A003": {
        "appointmentId": "MOCK-A003",
        "id": "MOCK-A003",
        "personId": "MOCK-P002",
        "eventId": "0e38e7a7-fcaa-447c-9ff6-b5255bc9c226",
        "resourceId": "MOCK-R002",
        "appointmentDate": _future_date(10, 14, 0),
        "isCancelled": False,
        "isRescheduled": False,
        "isKept": False,
        "details": "Ill Visit",
    },
}

_INSURANCES: dict[str, list[dict]] = {
    "MOCK-P001": [
        {
            "personId": "MOCK-P001",
            "personPayerId": "MOCK-INS-001",
            "payerId": "MOCK-PAY-001",
            "payerName": "Aetna",
            "defaultCob": 1,
            "policyEffectiveDate": "2024-01-01",
            "policyExpirationDate": "2025-12-31",
            "relationship": "Self",
            "isPatientInsurance": True,
            "isActive": True,
            "isDeleted": False,
            "isAvailable": True,
        },
    ],
    "MOCK-P002": [
        {
            "personId": "MOCK-P002",
            "personPayerId": "MOCK-INS-002",
            "payerId": "MOCK-PAY-002",
            "payerName": "Blue Cross",
            "defaultCob": 1,
            "policyEffectiveDate": "2024-06-01",
            "policyExpirationDate": "2026-05-31",
            "relationship": "Self",
            "isPatientInsurance": True,
            "isActive": True,
            "isDeleted": False,
            "isAvailable": True,
        },
    ],
}

_SLOTS: list[dict] = [
    {
        "id": "MOCK-SLOT-001",
        "startDate": _future_date(3, 9, 0),
        "endDate": _future_date(3, 9, 30),
        "appointmentCount": 0,
        "locationId": "MOCK-L001",
        "locationName": "Main Clinic",
        "resourceId": "MOCK-R001",
        "resourceName": "Dr. Smith",
        "eventId": "b5c6d1f8-1820-4c47-ad1a-d6e5e61c8d90",
        "durationMinutes": 30,
    },
    {
        "id": "MOCK-SLOT-002",
        "startDate": _future_date(3, 11, 0),
        "endDate": _future_date(3, 11, 30),
        "appointmentCount": 0,
        "locationId": "MOCK-L001",
        "locationName": "Main Clinic",
        "resourceId": "MOCK-R001",
        "resourceName": "Dr. Smith",
        "eventId": "b5c6d1f8-1820-4c47-ad1a-d6e5e61c8d90",
        "durationMinutes": 30,
    },
    {
        "id": "MOCK-SLOT-003",
        "startDate": _future_date(3, 14, 0),
        "endDate": _future_date(3, 14, 30),
        "appointmentCount": 0,
        "locationId": "MOCK-L001",
        "locationName": "Main Clinic",
        "resourceId": "MOCK-R001",
        "resourceName": "Dr. Smith",
        "eventId": "b5c6d1f8-1820-4c47-ad1a-d6e5e61c8d90",
        "durationMinutes": 30,
    },
    {
        "id": "MOCK-SLOT-004",
        "startDate": _future_date(4, 10, 0),
        "endDate": _future_date(4, 10, 30),
        "appointmentCount": 0,
        "locationId": "MOCK-L001",
        "locationName": "Main Clinic",
        "resourceId": "MOCK-R001",
        "resourceName": "Dr. Smith",
        "eventId": "b5c6d1f8-1820-4c47-ad1a-d6e5e61c8d90",
        "durationMinutes": 30,
    },
    {
        "id": "MOCK-SLOT-005",
        "startDate": _future_date(4, 15, 0),
        "endDate": _future_date(4, 15, 30),
        "appointmentCount": 0,
        "locationId": "MOCK-L001",
        "locationName": "Main Clinic",
        "resourceId": "MOCK-R001",
        "resourceName": "Dr. Smith",
        "eventId": "b5c6d1f8-1820-4c47-ad1a-d6e5e61c8d90",
        "durationMinutes": 30,
    },
]

_RESOURCES: dict[str, dict] = {
    "MOCK-R001": {
        "id": "MOCK-R001",
        "providerId": "MOCK-PROV-001",
        "resourceDisplayName": "Dr. Smith (Family Practice)",
        "resourceType": "Person",
    },
    "MOCK-R002": {
        "id": "MOCK-R002",
        "providerId": "MOCK-PROV-002",
        "resourceDisplayName": "Dr. Johnson (Internal Medicine)",
        "resourceType": "Person",
    },
}

_LOCATIONS: dict[str, dict] = {
    "MOCK-L001": {
        "id": "MOCK-L001",
        "name": "Main Clinic",
    },
}

_CANCEL_REASONS: list[dict] = [
    {"id": "MOCK-CR-001", "name": "Patient Request", "type": "as_cancel_reason"},
    {"id": "MOCK-CR-002", "name": "Scheduling Conflict", "type": "as_cancel_reason"},
    {"id": "MOCK-CR-003", "name": "No Longer Needed", "type": "as_cancel_reason"},
]

_RESCHEDULE_REASONS: list[dict] = [
    {"id": "MOCK-RR-001", "name": "Patient Request", "type": "as_resched_reason"},
    {"id": "MOCK-RR-002", "name": "Scheduling Conflict", "type": "as_resched_reason"},
]


class MockApiHandler:
    """
    A fully in-memory mock that mirrors the public API of the real NextGen handler.
    No HTTP calls, no secrets required. Mutations update in-memory state so
    conversations remain consistent within a single process lifecycle.
    """

    def __init__(self, conv) -> None:
        self.conv = conv
        # Deep-copy seed data so each handler instance shares the module-level
        # state (mutations persist across turns within the same process).
        # If you need per-conversation isolation, deep-copy here instead.

    # ------------------------------------------------------------------
    # Session
    # ------------------------------------------------------------------

    def ensure_session_id(self, **kwargs) -> str:
        return "MOCK-SESSION"

    # ------------------------------------------------------------------
    # Person / Patient
    # ------------------------------------------------------------------

    def lookup_patients(
        self,
        phone_number: str,
        date_of_birth: Optional[str] = None,
        **kwargs,
    ) -> list[Person]:
        # Strip non-digit chars for flexible matching
        digits = "".join(ch for ch in phone_number if ch.isdigit())
        person_ids = _PHONE_INDEX.get(digits, [])
        results: list[Person] = []
        for pid in person_ids:
            person_data = _PERSONS.get(pid)
            if person_data is None:
                continue
            if date_of_birth and person_data.get("dateOfBirth") != date_of_birth:
                continue
            results.append(Person.model_validate(person_data))
        return results

    def get_person(self, person_id: str) -> Optional[Person]:
        data = _PERSONS.get(person_id)
        if data is None:
            return None
        return Person.model_validate(data)

    def get_appointment(self, appointment_id: str, expand=None) -> Optional[Appointment]:
        data = _APPOINTMENTS.get(appointment_id)
        if data is None:
            return None
        return Appointment.model_validate(data)

    def create_patient(self, payload: PersonCreateRequest) -> Optional[Person]:
        new_id = _mock_id()
        person_data = {
            "id": new_id,
            "firstName": payload.first_name,
            "lastName": payload.last_name,
            "dateOfBirth": payload.date_of_birth,
            "sex": payload.sex,
            "homePhone": payload.home_phone,
            "cellPhone": payload.cell_phone,
            "isPatient": True,
        }
        _PERSONS[new_id] = person_data
        # Index by phone numbers
        for phone in [payload.home_phone, payload.cell_phone]:
            if phone:
                digits = "".join(ch for ch in phone if ch.isdigit())
                _PHONE_INDEX.setdefault(digits, []).append(new_id)
        return Person.model_validate(person_data)

    def update_person_cell_phone(self, person_id: str, cell_phone: str) -> Optional[Person]:
        data = _PERSONS.get(person_id)
        if data is None:
            return None
        old_cell = data.get("cellPhone")
        data["cellPhone"] = cell_phone
        # Update phone index
        if old_cell:
            old_digits = "".join(ch for ch in old_cell if ch.isdigit())
            if old_digits in _PHONE_INDEX and person_id in _PHONE_INDEX[old_digits]:
                _PHONE_INDEX[old_digits].remove(person_id)
        new_digits = "".join(ch for ch in cell_phone if ch.isdigit())
        _PHONE_INDEX.setdefault(new_digits, []).append(person_id)
        return Person.model_validate(data)

    # ------------------------------------------------------------------
    # Appointments
    # ------------------------------------------------------------------

    def get_person_appointments(
        self,
        person_id: str,
        start_date_iso: Optional[str] = None,
        end_date_iso: Optional[str] = None,
        **kwargs,
    ) -> list[Appointment]:
        results: list[Appointment] = []
        for appt in _APPOINTMENTS.values():
            if appt.get("personId") != person_id:
                continue
            appt_date = appt.get("appointmentDate", "")
            if start_date_iso and appt_date < start_date_iso:
                continue
            if end_date_iso and appt_date > end_date_iso:
                continue
            results.append(Appointment.model_validate(appt))
        # Sort by date
        results.sort(key=lambda a: a.appointment_date or "")
        return results

    def create_appointment(self, payload: AppointmentCreateRequest) -> Optional[Appointment]:
        new_id = _mock_id()
        appt_data = {
            "appointmentId": new_id,
            "id": new_id,
            "personId": payload.person_id,
            "eventId": payload.event_id,
            "resourceId": payload.resource_ids[0] if payload.resource_ids else None,
            "appointmentDate": payload.appointment_date,
            "isCancelled": False,
            "isRescheduled": False,
            "isKept": False,
            "details": payload.details or payload.description or "",
        }
        _APPOINTMENTS[new_id] = appt_data
        return Appointment.model_validate(appt_data)

    def cancel_appointment(
        self, appointment_id: str, cancel_reason_id: str
    ) -> Optional[Appointment]:
        appt = _APPOINTMENTS.get(appointment_id)
        if appt is None:
            return None
        appt["isCancelled"] = True
        return Appointment.model_validate(appt)

    def reschedule_appointment(
        self, appointment_id: str, payload: AppointmentRescheduleRequest
    ) -> Optional[Appointment]:
        old_appt = _APPOINTMENTS.get(appointment_id)
        if old_appt is None:
            return None
        # Mark old appointment as rescheduled
        old_appt["isRescheduled"] = True

        # Create a new appointment for the rescheduled slot
        new_id = _mock_id()
        new_appt = copy.deepcopy(old_appt)
        new_appt["appointmentId"] = new_id
        new_appt["id"] = new_id
        new_appt["appointmentDate"] = payload.appointment_date
        new_appt["isRescheduled"] = False
        new_appt["isCancelled"] = False
        new_appt["rescheduledAppointmentId"] = appointment_id
        if payload.event_id:
            new_appt["eventId"] = payload.event_id
        if payload.resource_ids:
            new_appt["resourceId"] = payload.resource_ids[0]
        if payload.location_id:
            new_appt["locationId"] = payload.location_id
        if payload.details:
            new_appt["details"] = payload.details
        _APPOINTMENTS[new_id] = new_appt
        return Appointment.model_validate(new_appt)

    # ------------------------------------------------------------------
    # Insurance
    # ------------------------------------------------------------------

    def get_person_insurances(self, person_id: str, **kwargs) -> list[PersonInsurance]:
        items = _INSURANCES.get(person_id, [])
        return [PersonInsurance.model_validate(ins) for ins in items]

    # ------------------------------------------------------------------
    # Slots / Availability
    # ------------------------------------------------------------------

    def search_appointment_slots(
        self,
        start_date_iso: str,
        end_date_iso: Optional[str] = None,
        location_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        **kwargs,
    ) -> list[AppointmentSlot]:
        results: list[AppointmentSlot] = []
        for slot in _SLOTS:
            slot_start = slot.get("startDate", "")
            if slot_start < start_date_iso:
                continue
            if end_date_iso and slot_start > end_date_iso:
                continue
            if location_id and slot.get("locationId") != location_id:
                continue
            if resource_id and slot.get("resourceId") != resource_id:
                continue
            results.append(AppointmentSlot.model_validate(slot))
        return results

    def search_appointment_availability(
        self, payload: AppointmentAvailabilityRequest
    ) -> list[AppointmentSlot]:
        return self.search_appointment_slots(
            start_date_iso=payload.date_range_start,
            end_date_iso=payload.date_range_end,
        )

    # ------------------------------------------------------------------
    # Resources
    # ------------------------------------------------------------------

    def list_resources(self, **kwargs) -> list[Resource]:
        return [Resource.model_validate(r) for r in _RESOURCES.values()]

    def get_resource(self, resource_id: str) -> Optional[Resource]:
        data = _RESOURCES.get(resource_id)
        if data is None:
            return None
        return Resource.model_validate(data)

    # ------------------------------------------------------------------
    # Reasons
    # ------------------------------------------------------------------

    def get_cancel_reasons(self, **kwargs) -> list[ListItem]:
        return [ListItem.model_validate(r) for r in _CANCEL_REASONS]

    def get_reschedule_reasons(self, **kwargs) -> list[ListItem]:
        return [ListItem.model_validate(r) for r in _RESCHEDULE_REASONS]

    # ------------------------------------------------------------------
    # Chart alerts (empty for mock)
    # ------------------------------------------------------------------

    def get_person_chart_alerts(self, person_id: str, **kwargs) -> list:
        return []


@func_description("Mock API handler for template project (no real API calls)")
def mock_api(conv: Conversation):
    pass
