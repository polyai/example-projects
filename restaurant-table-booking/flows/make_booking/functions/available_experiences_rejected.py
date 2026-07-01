import datetime as dt

from _gen import *  # <AUTO GENERATED>
from functions.check_availability import filter_availability
from functions.start_handle_over_max_group_size import start_handle_over_max_group_size


@func_description(
    "Should be called if user is not interested in the experience(s) offered. Checks is there is another suitable option we could offer"
)
@func_parameter("date", "Date of the selected booking slot, which must be in the YYYY-MM-DD format")
@func_parameter("time", "Time of the selected booking slot in HH:MM format, e.g. 15:00")
@func_parameter("party_size", "Party size for the booking")
def available_experiences_rejected(
    conv: Conversation, flow: Flow, date: str, time: str, party_size: str
):
    conv.state.experiences_rejected = True
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
        flow.goto_step(
            "Selected experience not available, no alternative availability at requested time"
        )
        return "Standard booking is not available for the requested time, so ask user for an alternative time."
    flow.goto_step("Selected experience not available, offer standard table")
    return "Standard booking is available, ask user if they would like to make that instead."
