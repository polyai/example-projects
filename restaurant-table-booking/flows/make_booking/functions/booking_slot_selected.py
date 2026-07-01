import datetime as dt

from _gen import *  # <AUTO GENERATED>
from functions.check_availability import (
    check_availability_including_experiences,
    filter_availability,
)
from functions.make_booking_utils import check_cancellation_policy
from functions.start_handle_over_max_group_size import start_handle_over_max_group_size


@func_description(
    "Calling this function doesn't confirm the booking, but it allows you to proceed in the booking flow and collect additional information you need to continue making the booking."
)
@func_parameter("date", "Date of the selected booking slot, which must be in the YYYY-MM-DD format")
@func_parameter("time", "Time of the selected booking slot in HH:MM format, e.g. 15:00")
@func_parameter("party_size", "Party size for the booking")
@func_parameter("experience_id", "selected experience id (or 0 if unknown)")
def booking_slot_selected(
    conv: Conversation, flow: Flow, date: str, time: str, party_size: int, experience_id: int
):
    conv.state.standard_booking_selected = False
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

    if experience_id:
        conv.write_metric("EXPERIENCES_REQUESTED", write_once=True)
        availability = filter_availability(availability, requested_experience_id=experience_id)
        conv.state.selected_experience = conv.state.active_experiences.get(experience_id)
        conv.state.selected_experience_formatted = conv.state.selected_experience["formatted"]
        conv.state.selected_experience_name = conv.state.selected_experience["name"]
        conv.write_metric(
            "SELECTED_EXPERIENCE_NAME",
            value=conv.state.selected_experience_name,
            write_once=True,
        )
        conv.state.party_size_per_price_type = None
        if price_info := conv.state.selected_experience.get("price_info"):
            if len(price_info["prices"]) != 1:
                conv.state.experience_price_options = price_info["prices"]
                conv.state.datetime_str = datetime_str
                conv.state.experience_id = experience_id
                conv.state.date = date
                conv.state.time = time
                conv.state.party_size = party_size
                flow.goto_step("Select price options")
                return "This experience has multiple price options. Let the user to select how many party members will want which option."
                # return try_transfer_call(conv, "multi_price_experience_selected", "Ok, I'll need to get one of my colleagues to help with this booking. One moment please.", "default")
            conv.state.total_price = price_info["prices"][0]["min_unit_amount"] * party_size
            conv.state.party_size_per_price_type = [
                {"id": price_info["prices"][0]["price_id"], "count": party_size}
            ]
    if datetime_str not in availability.get("times"):
        return check_availability_including_experiences(
            conv,
            flow,
            party_size,
            time,
            date,
            "-",
            [experience_id] if experience_id else [],
        )
    if experience_id:
        return check_cancellation_policy(
            conv, flow, datetime_str, experience_id, date, time, party_size
        )

    # decide if we should do upsell
    available_experiences = {}
    for _experience_id in conv.state.active_experiences or []:
        times_available_for_experience = filter_availability(
            availability, requested_experience_id=_experience_id
        ).get("times")
        if datetime_str in times_available_for_experience:
            available_experiences[_experience_id] = conv.state.active_experiences.get(
                _experience_id
            )

    ## if experiences are available
    if available_experiences:
        conv.write_metric("EXPERIENCES_AVAILABLE_TO_OFFER", write_once=True)
        if len(available_experiences) == 1:
            conv.write_metric("SINGLE_EXPERIENCE_OFFERED", write_once=True)
        else:
            conv.write_metric("MULTIPLE_EXPERIENCES_OFFERED", write_once=True)
        flow.goto_step("Upsell experiences")
        conv.state.available_experiences_formatted = "# Available experiences\n" + "\n\n".join(
            [experience["formatted"] for experience in available_experiences.values()]
        )
        conv.state.unavailable_experiences_formatted = "# Unavailable experiences\n" + "\n\n".join(
            [
                experience["formatted"]
                for experience in conv.state.active_experiences.values()
                if experience_id not in available_experiences
            ]
        )
        standard_availability = filter_availability(availability, requested_type="Standard")
        if datetime_str in standard_availability.get("times"):
            if len(available_experiences) == 1:
                return f"Tell user about the available experience: \n {conv.state.available_experiences_formatted} \n Ask if they would be interested in booking it, or if they would prefer to make a standard booking."
            return f"List out the available experiences. \n {conv.state.available_experiences_formatted} \n Then, ask if they would be interested in booking one of these options, or if they would prefer to make a standard booking."
        else:
            if len(available_experiences) == 1:
                return f"Tell user about the available experience: \n {conv.state.available_experiences_formatted} \n Confirm that the user is happy to book it. Don't explicitly offer standard booking (it's not available at this time, but you can still call standard_booking_selected to work out when it would be available)."
            return f"List out the available experiences. \n {conv.state.available_experiences_formatted} \n Then, ask user which one they want to book. Don't explicitly offer standard booking (it's not available at this time, but you can still call standard_booking_selected to work out when it would be available)."
    ## if experiences are not available, continue with booking
    return check_cancellation_policy(
        conv, flow, datetime_str, experience_id, date, time, party_size
    )
