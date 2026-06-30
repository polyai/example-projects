from datetime import datetime
from typing import Any, Optional

from _gen import *  # <AUTO GENERATED>
from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


class NextGenResponseModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class Person(NextGenResponseModel):
    id: str = Field(alias="id")
    first_name: Optional[str] = Field(default=None, alias="firstName")
    last_name: Optional[str] = Field(default=None, alias="lastName")
    date_of_birth: Optional[str] = Field(default=None, alias="dateOfBirth")
    sex: Optional[str] = Field(default=None, alias="sex")
    home_phone: Optional[str] = Field(default=None, alias="homePhone")
    cell_phone: Optional[str] = Field(default=None, alias="cellPhone")
    is_patient: Optional[bool] = Field(default=None, alias="isPatient")
    primary_care_provider_id: Optional[str] = Field(default=None, alias="primaryCareProviderId")
    uds_language_barrier_id: Optional[str] = Field(default=None, alias="udsLanguageBarrierId")
    # /persons/{id} uses preferredLanguageId; lookup may still send languageId.
    language_id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            "preferredLanguageId",
            "languageId",
        ),
    )


class Appointment(NextGenResponseModel):
    appointment_id: Optional[str] = Field(default=None, alias="appointmentId")
    id: Optional[str] = Field(default=None, alias="id")
    person_id: Optional[str] = Field(default=None, alias="personId")
    event_id: Optional[str] = Field(default=None, alias="eventId")
    resource_id: Optional[str] = Field(default=None, alias="resourceId")
    encounter_id: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("encounterId", "EncounterId")
    )
    appointment_date: Optional[str] = Field(default=None, alias="appointmentDate")
    is_cancelled: Optional[bool] = Field(default=None, alias="isCancelled")
    is_rescheduled: Optional[bool] = Field(default=None, alias="isRescheduled")
    rescheduled_appointment_id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("rescheduledAppointmentId", "RescheduledAppointmentId"),
    )
    is_kept: Optional[bool] = Field(default=None, alias="isKept")
    details: Optional[str] = Field(default=None, alias="details")


class AppointmentSlot(NextGenResponseModel):
    id: Optional[str] = Field(default=None, alias="id")
    start_date: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("startDate", "appointmentDateTime")
    )
    end_date: Optional[str] = Field(default=None, alias="endDate")
    appointment_count: Optional[int] = Field(default=None, alias="appointmentCount")
    location_id: Optional[str] = Field(default=None, alias="locationId")
    location_name: Optional[str] = Field(default=None, alias="locationName")
    resource_id: Optional[str] = Field(default=None, alias="resourceId")
    resource_name: Optional[str] = Field(default=None, alias="resourceName")
    resource_names: Optional[list[str]] = Field(default=None, alias="resourceNames")
    event_id: Optional[str] = Field(default=None, alias="eventId")
    category_id: Optional[str] = Field(default=None, alias="categoryId")
    begin_time: Optional[str] = Field(default=None, alias="beginTime")
    duration_minutes: Optional[int] = Field(
        default=None, validation_alias=AliasChoices("durationMinutes", "duration")
    )
    resource_ids: Optional[list[str]] = Field(default=None, alias="resourceIds")
    location_ids: Optional[list[str]] = Field(default=None, alias="locationIds")
    time_slot_count: Optional[int] = Field(
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
    person_id: Optional[str] = Field(default=None, alias="personId")
    recall_plan_id: Optional[str] = Field(default=None, alias="recallPlanId")
    id: Optional[int] = Field(default=None, alias="id")
    description: Optional[str] = Field(default=None, alias="description")
    is_active: Optional[bool] = Field(default=None, alias="isActive")
    expected_return_date: Optional[str] = Field(default=None, alias="expectedReturnDate")
    event_id: Optional[str] = Field(default=None, alias="eventId")
    event_description: Optional[str] = Field(default=None, alias="eventDescription")
    resource_id: Optional[str] = Field(default=None, alias="resourceId")
    location_id: Optional[str] = Field(default=None, alias="locationId")
    location_name: Optional[str] = Field(default=None, alias="locationName")


class Practice(NextGenResponseModel):
    id: Optional[str] = Field(default=None, alias="id")
    name: Optional[str] = Field(default=None, alias="name")


class Provider(NextGenResponseModel):
    id: Optional[str] = Field(default=None, alias="id")
    first_name: Optional[str] = Field(default=None, alias="firstName")
    last_name: Optional[str] = Field(default=None, alias="lastName")
    display_name: Optional[str] = Field(default=None, alias="displayName")


class Resource(NextGenResponseModel):
    id: Optional[str] = Field(default=None, alias="id")
    provider_id: Optional[str] = Field(default=None, alias="providerId")
    resource_display_name: Optional[str] = Field(default=None, alias="resourceDisplayName")
    resource_type: Optional[str] = Field(default=None, alias="resourceType")


class AppointmentCategory(NextGenResponseModel):
    id: Optional[str] = Field(default=None, alias="id")
    name: Optional[str] = Field(default=None, alias="name")


class Event(NextGenResponseModel):
    id: Optional[str] = Field(default=None, alias="id")
    name: Optional[str] = Field(default=None, alias="name")


class Location(NextGenResponseModel):
    id: Optional[str] = Field(default=None, alias="id")
    name: Optional[str] = Field(default=None, alias="name")


class Payer(NextGenResponseModel):
    id: Optional[str] = Field(default=None, alias="id")
    name: Optional[str] = Field(default=None, alias="name")


class PersonInsurance(NextGenResponseModel):
    person_id: Optional[str] = Field(default=None, alias="personId")
    person_payer_id: Optional[str] = Field(default=None, alias="personPayerId")
    payer_id: Optional[str] = Field(default=None, alias="payerId")
    payer_name: Optional[str] = Field(default=None, alias="payerName")
    default_cob: Optional[int] = Field(default=None, alias="defaultCob")
    policy_effective_date: Optional[str] = Field(default=None, alias="policyEffectiveDate")
    policy_expiration_date: Optional[str] = Field(default=None, alias="policyExpirationDate")
    insured_person_id: Optional[str] = Field(default=None, alias="insuredPersonId")
    relationship: Optional[str] = Field(default=None, alias="relationship")
    is_patient_insurance: Optional[bool] = Field(default=None, alias="isPatientInsurance")
    is_active: Optional[bool] = Field(default=None, alias="isActive")
    is_deleted: Optional[bool] = Field(default=None, alias="isDeleted")
    is_available: Optional[bool] = Field(default=None, alias="isAvailable")
    is_employer_insurance: Optional[bool] = Field(default=None, alias="isEmployerInsurance")
    links: Optional[list[dict[str, Any]]] = Field(default=None, alias="_links")


class ChartAlert(NextGenResponseModel):
    id: Optional[str] = Field(default=None, alias="id")
    person_id: Optional[str] = Field(default=None, alias="personId")
    message_id: Optional[str] = Field(default=None, alias="messageId")
    alert_type_id: Optional[str] = Field(default=None, alias="alertTypeId")
    alert_type_description: Optional[str] = Field(default=None, alias="alertTypeDescription")
    comment: Optional[str] = Field(default=None, alias="comment")
    description: Optional[str] = Field(default=None, alias="description")
    is_deleted: Optional[bool] = Field(default=None, alias="isDeleted")
    is_flagged: Optional[bool] = Field(default=None, alias="isFlagged")


class ListItem(NextGenResponseModel):
    id: Optional[str] = Field(default=None, alias="id")
    name: Optional[str] = Field(default=None, alias="name")
    type: Optional[str] = Field(default=None, alias="type")


@func_description("EHR API response models")
def nextgen_response_models(conv: Conversation):
    pass
