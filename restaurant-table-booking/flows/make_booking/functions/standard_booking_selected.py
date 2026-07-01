import datetime as dt

from _gen import *  # <AUTO GENERATED>
from functions.check_availability import filter_availability, sort_times_by_proximity
from functions.make_booking_utils import check_cancellation_policy
from functions.start_handle_over_max_group_size import start_handle_over_max_group_size


@func_description(
    "Call when user doesn't want to book any experiences, or selects standard booking"
)
@func_parameter("date", "Date of the selected booking slot, which must be in the YYYY-MM-DD format")
@func_parameter("time", "Time of the selected booking slot in HH:MM format, e.g. 15:00")
@func_parameter("party_size", "Party size for the booking")
def standard_booking_selected(
    conv: Conversation, flow: Flow, date: str, time: str, party_size: str
):
    conv.state.experiences_rejected = True
    conv.write_metric("EXPERIENCES_UPSELL_REJECTED", write_once=True)
    try:
        if int(party_size) >= int(conv.variant.large_party_size):
            return start_handle_over_max_group_size(conv, int(party_size))
        elif int(party_size) == 0:
            raise ValueError("Not a valid party size")
    except ValueError:
        return "You need to specify a party size. Ask the user if you don't know already."

    parsed_date = None
    try:
        parsed_date = dt.date.fromisoformat(date)
    except ValueError as e:
        # For example February 29th if it's not a leap year
        if str(e) == "day is out of range for month":
            return "The day is out of range for the month. Ask for a different date."
    if not parsed_date:
        return """The date you provided was in the wrong format. If you know the date requested by the user, please try calling
    this function again using the following format: YYYY-MM-DD. Otherwise, ask the user what day they would like to book."""

    parsed_time = None
    try:
        parsed_time = dt.time.fromisoformat(time)
    except ValueError:
        pass
    if not parsed_time:
        return """The time you provided was in the wrong format. If you know the time requested by the user, please try calling
    this function again using the following format: HH:MM. Otherwise, ask the user what time they would like to book."""

    datetime_obj = dt.datetime.combine(parsed_date, parsed_time)
    datetime_str = datetime_obj.strftime("%Y-%m-%dT%H:%M")

    availability = conv.state.availability_response

    conv.state.selected_experience = None
    conv.state.selected_experience_formatted = None
    conv.state.selected_experience_name = None
    availability = filter_availability(availability, requested_type="Standard")

    if datetime_str not in availability.get("times"):
        if not availability.get("times"):
            flow.goto_step("Standard booking not available")
            return "Standard booking is not within 3 hours of the requested time."
        if conv.current_flow == "make_booking":
            conv.write_metric("SUGGESTED_CLOSEST_AVAILABLE_TIME")
        else:
            conv.write_metric("AMEND_SUGGESTED_CLOSEST_AVAILABLE_TIME")
        alt_times = sort_times_by_proximity(conv, availability.get("times"), datetime_obj)
        flow.goto_step("Standard booking available near requested time")
        return (
            f"The requested time is not available for standard booking, only for experiences, but here are some alternatives: {alt_times}. "
            "Pick the first time and offer it as the nearest available time to the user. If the user refuses it, offer the next time. Keep in mind to offer at most 2 alternatives.\n"
            "# EXAMPLE CONVERSATION:\n"
            "AGENT: We don't have any tables free at 5pm tomorrow for standard bookings, only experiences. The nearest available slot we have is 6pm, would that work for you?\n"
            "USER: No\n"
            "AGENT: We also have space earlier at 3pm, would that be better?\n"
            "USER: No\n"
            "AGENT: Is there another date or time I could check for you?"
        )

    ## if experiences are not available, continue with booking
    return check_cancellation_policy(conv, flow, datetime_str, 0, date, time, party_size)
