from _gen import *  # <AUTO GENERATED>
from functions.handoff import handoff
from functions.routes_api_call import get_spots_and_routes_and_appointments_in_date_range
from functions.utils import (
    get_potential_slot,
    get_prompt_for_interior_vs_exterior_readback,
    get_prompt_for_new_appointment_timeframe_readback,
    get_start_and_end_date_for_search,
    increment_date_by_one,
)


@func_description(
    "check slot availability to reschedule the user's appointment to, nb make sure that start_time and end_time are at least 2 hours apart"
)
@func_parameter(
    "date",
    'Default to "NA". If the user wants to schedule for a specific date, set to this date. Should be in a YYYY-MM-DD format. Accommodate for generic timeframe like "early" or "late" with a sensible date, for example if the user says "early May" set to the start of the month (2025-05-01), if the user says "late May" set to the end of the month (2025-05-31), and if the user just says "May" set to the middle of the month (2025-05-15). NOTE: If the user only says something like "early" or "earlier" without specific any time range then set this to the date after the current date. If the user provided a preferred date earlier in the conversation and wants to find another slot in the same day, use that same day.',
)
@func_parameter(
    "start_time",
    'Default to "NA". If the user wants to schedule for a specific time (or an arrival time no earlier than this), set to this time. Should be converted to HH:MM format (e.g. 13:10). If the user says "morning", set to "08:00" , if the user says "afternoon", set to "13:00". If they say "later in the day" set to a later time than the original appointment. NOTE: If the user only says something like "early" or "earlier" without specific any time range then set this to "08:00"',
)
@func_parameter(
    "end_time",
    'Default to "NA" if no start_time. If filling in start_time, set end_time to "13:00" if the user says "morning" (NOT "12:00", should be "13:00" for morning), and set to "20:00" if the user says "afternoon". otherwise, default to two hours after the given start time unless user is explicit about a specific time that we shouldn\'t arrive at their property later than, e.g. if the user says "can you come at 9 in the morning", set this to "11:00", and eg if the user says "can you come between 1 and 4 in the afternoon", set this to "16:00"',
)
@func_latency_control(
    delay_before_responses_start=0,
    silence_after_each_response=3,
    delay_responses=[
        ("one moment please while I check up our system ", 3),
        ("one more moment please", 2),
        ("sorry it's taking me a bit of time...", 3),
        ("okay, let's see...", 3),
    ],
)
def check_slot_availability(
    conv: Conversation, flow: Flow, date: str, start_time: str, end_time: str
):
    conv.write_metric("DATE_COLLECTED", None)
    conv.write_metric("TIME_COLLECTED", None)

    if getattr(conv.state, "USE_MOCK_API", False):
        from datetime import datetime, timedelta

        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        slot_date = date if date != "NA" else tomorrow
        slot_start = start_time if start_time != "NA" else "09:00"
        slot_end = end_time if end_time != "NA" else "12:00"
        slot = {
            "date": slot_date,
            "start": slot_start,
            "end": slot_end,
            "spotID": "MOCK-SPOT-001",
            "routeID": "MOCK-R001",
        }
        conv.state.potential_slot = slot
        flow.goto_step("Reschedule appointment")
        timeframe = get_prompt_for_new_appointment_timeframe_readback(slot_start, slot_end)
        conv.state.new_appointment_timeframe_readback = timeframe
        appointment = conv.state.appointment
        return (
            f"You have found a new slot on {slot_date}. "
            f'Tell the user: "Looks like we can reschedule to {slot_date}{timeframe}. '
            f'Would you like me to go ahead and reschedule?"'
        )

    # Check if it's winter
    is_winter = False
    is_too_late = False
    try:
        if date != "NA":
            slot_date = datetime.strptime(date, "%Y-%m-%d")
            month = slot_date.month
            is_winter = month in [12, 1, 2]  # December, January, February

            # Check if the requested time starts after 4pm (16:00) or ends after 5pm (17:00)
            # Time strings in "HH:MM" format can be compared directly as strings
            if start_time != "NA" and start_time > "16:00":
                is_too_late = True

            if start_time == "16:00":
                end_time = "17:00"
            elif end_time != "NA" and end_time > "17:00":
                is_too_late = True
    except (ValueError, TypeError):
        pass

    if is_winter and is_too_late:
        flow.goto_step("Negotiate modified visit")
        return """Tell the user: "Our latest winter appointment is 4 to 5 pm. Would that or an earlier time work for you?"""

    if date == "NA":
        date_to_search = increment_date_by_one(conv.state.current_date_ymd)
    else:
        date_to_search = date

    start_and_end = get_start_and_end_date_for_search(date_to_search, conv.state.current_date_ymd)
    start_date = start_and_end["start_date"]
    end_date = start_and_end["end_date"]

    try:
        spots, routes, appointments = get_spots_and_routes_and_appointments_in_date_range(
            conv, start_date, end_date
        )
    except Exception:
        conv.log.error("API or logic error", exc_info=True)
        handoff_reason = "API_TIMEOUT" if conv.state.api_timeout else "API_ERROR"
        return handoff(
            conv,
            handoff_reason,
            "I'm afraid I am facing some technical difficulties at this moment, let me put you through to someone who can help, just a moment please!",
            "CUSTOMER_CARE",
        )

    appointment = conv.state.appointment
    if appointment is None:
        raise ValueError("appointment must be set before calling this function")
    if slot := get_potential_slot(
        conv,
        spots=spots,
        routes=routes,
        appointments=appointments,
        duration=appointment["duration"],
        max_distance_to_previous_spot_in_miles=5,
        max_distance_to_closest_spot_in_miles=10,
        service_type_id_for_warranty_reservice=conv.state.service_type_id_for_warranty_reservice,
        current_date=conv.state.current_date_ymd,
        requested_date=date if date != "NA" else None,
        requested_start_time=start_time if start_time != "NA" else None,
        requested_end_time=end_time if end_time != "NA" else None,
        existing_appointment_date=appointment["date"],
    ):
        conv.log.info("Potential slot to offer", slot=slot)
        conv.state.potential_slot = slot
        flow.goto_step("Reschedule appointment")
        date = slot["date"]
        start = slot.get("start")
        end = slot.get("end")
        interior_vs_exterior_readback = get_prompt_for_interior_vs_exterior_readback(
            appointment["doInterior"] == "2"
        )
        if start and end:
            timeframe_readback = get_prompt_for_new_appointment_timeframe_readback(start, end)
            conv.state.new_appointment_timeframe_readback = timeframe_readback
            return f"""You have found a potential time slot {slot}. You now need to get confirmation from the user whether the date and time works for them. Tell the user: "Looks like we can get someone out there on {date} and arrive at your property {timeframe_readback}." Would you like me to schedule your appointment for that time?"""
        else:
            timeframe_readback = get_prompt_for_new_appointment_timeframe_readback("08:00", "20:00")
            conv.state.new_appointment_timeframe_readback = timeframe_readback
            return f"""You have found a potential date {slot}. You now need to get confirmation from the user whether the date works for them. Tell the user: "Looks like we can get someone out there on {date} {timeframe_readback} {interior_vs_exterior_readback}. Would you like me to schedule your appointment for that day?"""

    return handoff(
        conv,
        "NO_AVAILABILITY_FOUND",
        "I'm afraid I cannot find any availablility at the moment, let me put you through to someone who can help, just a moment please!",
        "CUSTOMER_CARE",
    )
