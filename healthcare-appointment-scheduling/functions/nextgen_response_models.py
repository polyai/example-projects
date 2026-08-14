from datetime import datetime
from typing import Any

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from _gen import *  # <AUTO GENERATED>


class NextGenResponseModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class Person(NextGenResponseModel):
    id: str = Field(alias="id")
    first_name: str | None = Field(default=None, alias="firstName")
    last_name: str | None = Field(default=None, alias="lastName")
    date_of_birth: str | None = Field(default=None, alias="dateOfBirth")
    sex: str | None = Field(default=None, alias="sex")
    home_phone: str | None = Field(default=None, alias="homePhone")
    cell_phone: str | None = Field(default=None, alias="cellPhone")
    is_patient: bool | None = Field(default=None, alias="isPatient")
    primary_care_provider_id: str | None = Field(
        default=None, alias="primaryCareProviderId"
    )
    uds_language_barrier_id: str | None = Field(
        default=None, alias="udsLanguageBarrierId"
    )
    # /persons/{id} uses preferredLanguageId; lookup may still send languageId.
    language_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "preferredLanguageId",
            "languageId",
        ),
    )


class Appointment(NextGenResponseModel):
    appointment_id: str | None = Field(default=None, alias="appointmentId")
    id: str | None = Field(default=None, alias="id")
    person_id: str | None = Field(default=None, alias="personId")
    event_id: str | None = Field(default=None, alias="eventId")
    resource_id: str | None = Field(default=None, alias="resourceId")
    encounter_id: str | None = Field(
        default=None, validation_alias=AliasChoices("encounterId", "EncounterId")
    )
    appointment_date: str | None = Field(default=None, alias="appointmentDate")
    is_cancelled: bool | None = Field(default=None, alias="isCancelled")
    is_rescheduled: bool | None = Field(default=None, alias="isRescheduled")
    rescheduled_appointment_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "rescheduledAppointmentId", "RescheduledAppointmentId"
        ),
    )
    is_kept: bool | None = Field(default=None, alias="isKept")
    details: str | None = Field(default=None, alias="details")


class AppointmentSlot(NextGenResponseModel):
    id: str | None = Field(default=None, alias="id")
    start_date: str | None = Field(
        default=None, validation_alias=AliasChoices("startDate", "appointmentDateTime")
    )
    end_date: str | None = Field(default=None, alias="endDate")
    appointment_count: int | None = Field(default=None, alias="appointmentCount")
    location_id: str | None = Field(default=None, alias="locationId")
    location_name: str | None = Field(default=None, alias="locationName")
    resource_id: str | None = Field(default=None, alias="resourceId")
    resource_name: str | None = Field(default=None, alias="resourceName")
    resource_names: list[str] | None = Field(default=None, alias="resourceNames")
    event_id: str | None = Field(default=None, alias="eventId")
    category_id: str | None = Field(default=None, alias="categoryId")
    begin_time: str | None = Field(default=None, alias="beginTime")
    duration_minutes: int | None = Field(
        default=None, validation_alias=AliasChoices("durationMinutes", "duration")
    )
    resource_ids: list[str] | None = Field(default=None, alias="resourceIds")
    location_ids: list[str] | None = Field(default=None, alias="locationIds")
    time_slot_count: int | None = Field(
        default=None, validation_alias=AliasChoices("timeSlotCount", "timeslotCount")
    )

    @model_validator(mode="after")
    def normalize_start_date(self):
        """
        Normalize slot datetime across payload variants:
        - /appointments/slots: startDate + beginTime
        - /appointments/availability: appointmentDateTime
        """
        if not self.start_date:
            return self

        if not self.begin_time:
            return self

        date_text = str(self.start_date).strip()
        begin_text = str(self.begin_time).strip()
        if not date_text or not begin_text:
            return self

        try:
            base = datetime.fromisoformat(date_text.replace("Z", "+00:00"))
        except ValueError:
            return self

        digits = "".join(ch for ch in begin_text if ch.isdigit())
        if len(digits) == 3:
            digits = f"0{digits}"
        if len(digits) < 4:
            return self
        hour = int(digits[0:2])
        minute = int(digits[2:4])
        if hour > 23 or minute > 59:
            return self

        normalized = base.replace(hour=hour, minute=minute, second=0, microsecond=0)
        self.start_date = normalized.isoformat()
        return self


class RecallPlan(NextGenResponseModel):
    person_id: str | None = Field(default=None, alias="personId")
    recall_plan_id: str | None = Field(default=None, alias="recallPlanId")
    id: int | None = Field(default=None, alias="id")
    description: str | None = Field(default=None, alias="description")
    is_active: bool | None = Field(default=None, alias="isActive")
    expected_return_date: str | None = Field(
        default=None, alias="expectedReturnDate"
    )
    event_id: str | None = Field(default=None, alias="eventId")
    event_description: str | None = Field(default=None, alias="eventDescription")
    resource_id: str | None = Field(default=None, alias="resourceId")
    location_id: str | None = Field(default=None, alias="locationId")
    location_name: str | None = Field(default=None, alias="locationName")


class Practice(NextGenResponseModel):
    id: str | None = Field(default=None, alias="id")
    name: str | None = Field(default=None, alias="name")


class Provider(NextGenResponseModel):
    id: str | None = Field(default=None, alias="id")
    first_name: str | None = Field(default=None, alias="firstName")
    last_name: str | None = Field(default=None, alias="lastName")
    display_name: str | None = Field(default=None, alias="displayName")


class Resource(NextGenResponseModel):
    id: str | None = Field(default=None, alias="id")
    provider_id: str | None = Field(default=None, alias="providerId")
    resource_display_name: str | None = Field(
        default=None, alias="resourceDisplayName"
    )
    resource_type: str | None = Field(default=None, alias="resourceType")


class AppointmentCategory(NextGenResponseModel):
    id: str | None = Field(default=None, alias="id")
    name: str | None = Field(default=None, alias="name")


class Event(NextGenResponseModel):
    id: str | None = Field(default=None, alias="id")
    name: str | None = Field(default=None, alias="name")


class Location(NextGenResponseModel):
    id: str | None = Field(default=None, alias="id")
    name: str | None = Field(default=None, alias="name")


class Payer(NextGenResponseModel):
    id: str | None = Field(default=None, alias="id")
    name: str | None = Field(default=None, alias="name")


class PersonInsurance(NextGenResponseModel):
    person_id: str | None = Field(default=None, alias="personId")
    person_payer_id: str | None = Field(default=None, alias="personPayerId")
    payer_id: str | None = Field(default=None, alias="payerId")
    payer_name: str | None = Field(default=None, alias="payerName")
    default_cob: int | None = Field(default=None, alias="defaultCob")
    policy_effective_date: str | None = Field(
        default=None, alias="policyEffectiveDate"
    )
    policy_expiration_date: str | None = Field(
        default=None, alias="policyExpirationDate"
    )
    insured_person_id: str | None = Field(default=None, alias="insuredPersonId")
    relationship: str | None = Field(default=None, alias="relationship")
    is_patient_insurance: bool | None = Field(
        default=None, alias="isPatientInsurance"
    )
    is_active: bool | None = Field(default=None, alias="isActive")
    is_deleted: bool | None = Field(default=None, alias="isDeleted")
    is_available: bool | None = Field(default=None, alias="isAvailable")
    is_employer_insurance: bool | None = Field(
        default=None, alias="isEmployerInsurance"
    )
    links: list[dict[str, Any]] | None = Field(default=None, alias="_links")


class ChartAlert(NextGenResponseModel):
    id: str | None = Field(default=None, alias="id")
    person_id: str | None = Field(default=None, alias="personId")
    message_id: str | None = Field(default=None, alias="messageId")
    alert_type_id: str | None = Field(default=None, alias="alertTypeId")
    alert_type_description: str | None = Field(
        default=None, alias="alertTypeDescription"
    )
    comment: str | None = Field(default=None, alias="comment")
    description: str | None = Field(default=None, alias="description")
    is_deleted: bool | None = Field(default=None, alias="isDeleted")
    is_flagged: bool | None = Field(default=None, alias="isFlagged")


class ListItem(NextGenResponseModel):
    id: str | None = Field(default=None, alias="id")
    name: str | None = Field(default=None, alias="name")
    type: str | None = Field(default=None, alias="type")


@func_description("EHR API response models")
def nextgen_response_models(conv: Conversation):
    pass
