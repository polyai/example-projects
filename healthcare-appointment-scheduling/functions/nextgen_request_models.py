
from pydantic import BaseModel, ConfigDict, Field

from _gen import *  # <AUTO GENERATED>


class NextGenRequestModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")


class PersonCreateRequest(NextGenRequestModel):
    first_name: str = Field(alias="FirstName")
    last_name: str = Field(alias="LastName")
    date_of_birth: str = Field(alias="DateOfBirth")
    sex: str = Field(alias="Sex")
    home_phone: str | None = Field(default=None, alias="HomePhone")
    cell_phone: str | None = Field(default=None, alias="CellPhone")
    has_phone_number: bool = Field(default=True, alias="HasPhoneNumber")
    has_voice: bool = Field(default=True, alias="HasVoice")
    uses_sms: bool = Field(default=False, alias="UsesSms")
    uses_portal: bool = Field(default=False, alias="UsesPortal")
    has_email: bool = Field(default=False, alias="HasEmail")
    is_opt_out: bool = Field(default=False, alias="IsOptOut")
    ignore_duplicate_persons: bool = Field(default=True, alias="IgnoreDuplicatePersons")


class AppointmentCreateRequest(NextGenRequestModel):
    person_id: str = Field(alias="PersonId")
    event_id: str = Field(alias="EventId")
    location_id: str = Field(alias="LocationId")
    resource_ids: list[str] = Field(alias="ResourceIds")
    appointment_date: str = Field(alias="AppointmentDate")
    duration_minutes: int = Field(alias="DurationMinutes")
    details: str | None = Field(default=None, alias="Details")
    description: str | None = Field(default=None, alias="Description")
    rendering_provider_id: str | None = Field(
        default=None, alias="RenderingProviderId"
    )
    category_id: str | None = Field(default=None, alias="CategoryId")
    allow_double_booking: bool = Field(default=False, alias="AllowDoubleBooking")
    allow_category_conflict_override: bool = Field(
        default=False, alias="AllowCategoryConflictOverride"
    )
    conflict_override_on_login: bool = Field(
        default=False, alias="ConflictOverrideOnLogin"
    )
    allow_event_location_override: bool = Field(
        default=False, alias="AllowEventLocationOverride"
    )


class AppointmentRescheduleRequest(NextGenRequestModel):
    appointment_date: str = Field(alias="AppointmentDate")
    duration_minutes: int = Field(alias="DurationMinutes")
    location_id: str | None = Field(default=None, alias="LocationId")
    event_id: str | None = Field(default=None, alias="EventId")
    resource_ids: list[str] | None = Field(default=None, alias="ResourceIds")
    reschedule_reason_id: str | None = Field(
        default=None, alias="RescheduleReasonId"
    )
    details: str | None = Field(default=None, alias="Details")
    description: str | None = Field(default=None, alias="Description")


class FindPersonRescheduledAppointmentRequest(NextGenRequestModel):
    person_id: str = Field(alias="PersonId")
    original_appointment_id: str = Field(alias="RescheduledAppointmentId")
    end_date_iso: str = Field(alias="EndDate")
    start_date_iso: str | None = Field(default=None, alias="StartDate")
    top: int = Field(default=400, alias="Top")
    fetch_all_pages: bool = Field(default=True, alias="FetchAllPages")
    max_pages: int = Field(default=50, alias="MaxPages")


class AppointmentPatchRequest(NextGenRequestModel):
    details: str | None = Field(default=None, alias="Details")
    description: str | None = Field(default=None, alias="Description")
    procedure_with_resident: bool | None = Field(
        default=None, alias="ProcedureWithResident"
    )
    is_retained: bool | None = Field(default=None, alias="IsRetained")
    retained_appointment_id: str | None = Field(
        default=None, alias="RetainedAppointmentId"
    )
    rendering_provider_id: str | None = Field(
        default=None, alias="RenderingProviderId"
    )
    referring_provider_id: str | None = Field(
        default=None, alias="ReferringProviderId"
    )
    user_defined_1: str | None = Field(default=None, alias="UserDefined1")
    user_defined_2: str | None = Field(default=None, alias="UserDefined2")
    user_defined_3: str | None = Field(default=None, alias="UserDefined3")
    user_defined_4: str | None = Field(default=None, alias="UserDefined4")
    user_defined_5: str | None = Field(default=None, alias="UserDefined5")
    user_defined_6: str | None = Field(default=None, alias="UserDefined6")
    user_defined_7: str | None = Field(default=None, alias="UserDefined7")
    user_defined_8: str | None = Field(default=None, alias="UserDefined8")
    marketing_plan_id: str | None = Field(default=None, alias="MarketingPlanId")
    marketing_source_id: str | None = Field(default=None, alias="MarketingSourceId")
    marketing_plan_comments: str | None = Field(
        default=None, alias="MarketingPlanComments"
    )
    case_management_case_id: str | None = Field(
        default=None, alias="CaseManagementCaseId"
    )
    appointment_confirmed: bool | None = Field(
        default=None, alias="AppointmentConfirmed"
    )
    virtual_visit_link: str | None = Field(default=None, alias="VirtualVisitLink")
    encounter_id: str | None = Field(default=None, alias="EncounterId")


class AppointmentAvailabilityRequest(NextGenRequestModel):
    event_id: str | None = Field(default=None, alias="EventId")
    category_id: str | None = Field(default=None, alias="CategoryId")
    class_id: str | None = Field(default=None, alias="ClassId")
    resource_ids: list[str] | None = Field(default=None, alias="ResourceIds")
    group_resources_by_slot: bool | None = Field(
        default=None, alias="GroupResourcesBySlot"
    )
    location_ids: list[str] | None = Field(default=None, alias="LocationIds")
    date_range_start: str = Field(alias="DateRangeStart")
    date_range_end: str = Field(alias="DateRangeEnd")
    time_range_start: str | None = Field(default=None, alias="TimeRangeStart")
    time_range_end: str | None = Field(default=None, alias="TimeRangeEnd")
    duration_minutes: int | None = Field(default=None, alias="DurationMinutes")
    days_of_week: list[int] | None = Field(default=None, alias="DaysOfWeek")
    restrict_results_by: int | None = Field(default=None, alias="RestrictResultsBy")


class RecallPlanCreateRequest(NextGenRequestModel):
    recall_plan_id: str = Field(alias="RecallPlanId")
    last_date: str = Field(alias="LastDate")
    return_date: str = Field(alias="ReturnDate")
    event_id: str = Field(alias="EventId")
    resource_id: str | None = Field(default=None, alias="ResourceId")
    location_id: str | None = Field(default=None, alias="LocationId")
    note: str | None = Field(default=None, alias="Note")


class RecallPlanUpdateRequest(NextGenRequestModel):
    stop: bool | None = Field(default=None, alias="Stop")
    stop_reason_id: str | None = Field(default=None, alias="StopReasonId")
    recall_plan_id: str | None = Field(default=None, alias="RecallPlanId")
    last_date: str | None = Field(default=None, alias="LastDate")
    return_date: str | None = Field(default=None, alias="ReturnDate")
    event_id: str | None = Field(default=None, alias="EventId")
    resource_id: str | None = Field(default=None, alias="ResourceId")
    location_id: str | None = Field(default=None, alias="LocationId")
    note: str | None = Field(default=None, alias="Note")


@func_description("EHR API request models")
def nextgen_request_models(conv: Conversation):
    pass
