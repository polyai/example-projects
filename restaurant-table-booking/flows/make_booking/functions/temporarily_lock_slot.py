import datetime as dt

import plog

from _gen import *  # <AUTO GENERATED>
from functions.check_availability import (
    filter_availability,
    sort_times_by_proximity,
    valid_table_types,
)
from functions.make_booking_utils import _temporarily_lock_slot


@func_description(
    "Temporarily lock a booking slot for the user. It's not used to book the table of finalize the booking."
)
@func_parameter("date", "Date of the requested booking slot, in YYYY-MM-DD format")
@func_parameter(
    "time", "Time of the requested booking slot in HH:MM format, e.g. 15:00"
)
@func_parameter("party_size", "Party size for the booking")
@func_parameter(
    "selected_table_type",
    'Selected table type for booking ("default", "outdoor", "bar", "highTop", "counter")',
)
@plog.tmp_bind(api_integration="opentable")
def temporarily_lock_slot(
    conv: Conversation,
    flow: Flow,
    date: str,
    time: str,
    party_size: int,
    selected_table_type: str,
):
    if selected_table_type == "standard":
        selected_table_type = "default"
    elif not selected_table_type or selected_table_type not in valid_table_types:
        if conv.state.table_type_selection_enabled:
            return "You must specify a valid table type and call this function again."
        else:
            selected_table_type = "default"
    # Parse values
    parsed_date = None
    try:
        parsed_date = dt.date.fromisoformat(date)
    except ValueError:
        pass
    if not parsed_date:
        return """The date you provided was in the wrong format. If you know the date requested by the user, please try again
    using the following format: dd/mm/yyyy. Otherwise, ask the user what day they would like to book."""

    parsed_time = None
    try:
        parsed_time = dt.time.fromisoformat(time)
    except ValueError:
        pass
    if not parsed_time:
        return """The time you provided was in the wrong format. If you know the time requested by the user, please try again
    using the following format: 11:00. Otherwise, ask the user what time they would like to book."""
    parsed_datetime = dt.datetime.combine(parsed_date, parsed_time)
    datetime_str = parsed_datetime.strftime("%Y-%m-%dT%H:%M")

    data = conv.state.availability_response
    experience_id = (
        conv.state.selected_experience.get("experience_id")
        if conv.state.selected_experience
        else None
    )
    booking_type = "Experience" if conv.state.selected_experience else "Standard"
    availability_for_selected_table_type = filter_availability(
        data,
        requested_table_type=selected_table_type,
        requested_experience_id=experience_id,
        requested_type=booking_type,
    )
    if datetime_str not in availability_for_selected_table_type.get("times"):
        alt_times = sort_times_by_proximity(
            conv, availability_for_selected_table_type.get("times"), parsed_datetime
        )
        availability_for_other_table_types = filter_availability(
            data,
            requested_table_type=None,
            requested_experience_id=experience_id,
            requested_type=booking_type,
        )
        available_table_types = set()
        for time_entry in availability_for_other_table_types["times_available"]:
            if time_entry.get("time") == datetime_str:
                for availability in time_entry["availability_types"]:
                    for area in availability["diningArea"]:
                        available_table_types.update(area.get("table_type", []))
        conv.state.available_table_types = sorted(
            available_table_types & valid_table_types
        )
        available_types = ", ".join(
            "standard" if t == "default" else t
            for t in conv.state.available_table_types
        )
        flow.goto_step("Requested table type not available at requested time")
        return (
            f"There is a table available at the requested time, but not {selected_table_type}. "
            f"Suggest the next available time for the table type they want from '{alt_times}' remembering that indoors/inside is referring to a 'default' table. "
            if alt_times
            else f"It looks like there is no availability for {selected_table_type} within 3 hours of the requested time."
            f"These table types are available at the requested time: {available_types}. "
            "Say 'standard' instead of 'default'. "
            "If the user selects 'standard', save 'default' as selected_table_type. "
            "If the user gives a synonym (e.g., 'indoors', 'outside seating'), map it to the closest valid value."
        )

    return _temporarily_lock_slot(
        conv, flow, date, time, party_size, selected_table_type
    )
