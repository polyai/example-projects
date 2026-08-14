from _gen import *  # <AUTO GENERATED>
from flows.schedule_appointment.functions.find_slot_availability import (
    find_slot_availability,
)
from functions.handoff import handoff


@func_description("save any given appointment details")
@func_parameter(
    "service_ids",
    "The ID(s) of the service type(s) selected by the user, matched exactly from the service map. Do not infer or guess IDs if no exact match is found. Format as a comma-separated string, e.g. '9441,9442'.",
)
@func_parameter(
    "service_location",
    'a description of where exactly the issue is located eg "kitchen", "bedroom drawer", "flowerbed outside front door"',
)
@func_parameter("interior_needed", "if the user needs an interior service, set to True")
@func_parameter(
    "service_names",
    "A readable string of the service type name(s) as found in the service map, based on exact matches from the user's input. Combine using commas and 'and' for natural phrasing. Do not include any service type not found in the service map.",
)
@func_parameter(
    "user_said_service_not_in_map",
    "Set to true if the user names a service type that does not exist in the service map. Otherwise, set to false.",
)
@func_latency_control(
    delay_before_responses_start=0,
    silence_after_each_response=3,
    delay_responses=[
        ("Just taking notes here ...", 3),
        ("one second please...", 3),
        ("okay, let me see...", 3),
        ("Give me one more moment", 3),
    ],
)
def save_appointment_details(
    conv: Conversation,
    flow: Flow,
    service_ids: str,
    service_location: str,
    interior_needed: bool,
    service_names: str,
    user_said_service_not_in_map: bool,
):
    target_service_ids = []
    service_map = conv.state.services_map or []
    if service_map:
        for service_entry in service_map:
            for sid in list(service_ids.split(",")):
                if sid.lower() == service_entry["serviceID"].lower():
                    target_service_ids.append(service_entry["serviceID"])
                    conv.write_metric("SERVICE_TYPE_COLLECTED", service_entry["name"])
                    break
    else:
        target_service_ids = [s.strip() for s in service_ids.split(",") if s.strip()]
        for name in service_names.split(","):
            conv.write_metric("SERVICE_TYPE_COLLECTED", name.strip())
    conv.state.target_service_ids = ",".join(target_service_ids)
    conv.state.service_names = service_names

    if user_said_service_not_in_map:
        return handoff(
            conv,
            "SERVICE_NOT_AVAILABLE",
            "Let me put you through to someone who can help, just a moment please!",
            "CUSTOMER_CARE",
        )

    if interior_needed:
        conv.write_metric("INTERIOR_SERVICE_NEEDED", None)
        conv.state.interior_needed = 2
    else:
        conv.state.interior_needed = 1

    conv.state.service_location = service_location
    conv.write_metric("SERVICE_LOCATION_COLLECTED", service_location)

    flow.goto_step("Negotiate appointment time")
    slot_availability = find_slot_availability(
        conv=conv, flow=flow, date="NA", start_time="NA", end_time="NA"
    )
    # HACK, because find_slot_availability can return a string or handoff instructions in cases where the API fails or there is no availability
    if isinstance(slot_availability, str):
        return (
            f"You now have the service location as {service_location}, know that the user does {'' if interior_needed else 'not'} need an interior service, and the service types as {service_names}."
            + slot_availability
        )
    return slot_availability
