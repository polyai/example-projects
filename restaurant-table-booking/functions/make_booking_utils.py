import datetime as dt
import math
from http import HTTPStatus

import plog
from _gen import *  # <AUTO GENERATED>
from functions.check_availability import (
    check_availability,
    filter_availability,
    valid_table_types,
)
from functions.check_availability import (
    check_cancellation_policy as check_cancellation_policy_old,
)
from functions.opentable_api import get_restaurant_api
from functions.start_handle_over_max_group_size import start_handle_over_max_group_size
from functions.try_transfer_call import try_transfer_call

BASE_URL = "https://platform.opentable.com/inhouse/v1"
TIMEOUT = 8


@func_description("NOT TO BE CALLED DIRECTLY. Global utils for make_booking flow")
def make_booking_utils(conv: Conversation):
    # Add your function definition here.
    # You can optionally return a string that will be fed back to the LLM.
    pass


@plog.tmp_bind(api_integration="opentable")
def _temporarily_lock_slot(
    conv: Conversation,
    flow,
    date: str,
    time: str,
    party_size: int,
    selected_table_type: str,
):
    if selected_table_type == "standard":
        selected_table_type = "default"
    if selected_table_type not in ["-", "default"] and not conv.state.table_type_selection_enabled:
        conv.state.saved_table_type = selected_table_type
    if selected_table_type == "-":
        return "Selected table type is not specified. You can get available table types by calling check_availability."
    try:
        if int(party_size) >= int(conv.variant.large_party_size):
            return start_handle_over_max_group_size(conv, int(party_size))
        elif int(party_size) == 0:
            raise ValueError("Not a valid party size")
    except ValueError:
        return "You need to specify a party size. Ask the user if you don't know already."

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
    # edge case - temp lock slot called but we don't actually know availability
    # try seeing if there is availability first, continue if there is, or offer alternatives if there isn't
    if not conv.state.availability_response or parsed_datetime.strftime(
        "%Y-%m-%dT%H:%M"
    ) not in conv.state.availability_response.get("times", []):
        res = check_availability(conv, date, time, party_size, selected_table_type)
        if parsed_datetime.strftime("%Y-%m-%dT%H:%M") not in conv.state.availability_response.get(
            "times", []
        ):
            return res

    if conv.state.need_to_check_cancellation_policy:
        check_cancellation_policy_old(conv, parsed_datetime.strftime("%Y-%m-%dT%H:%M"))

        if conv.state.cancellation_type == "Hold":
            return "This booking requires card hold. Once the booking is complete, tell the user they will receive an SMS asking for their credit card details to secure the booking and ask if they would still like to proceed. If they do, call temporary_lock_slot again with the same values."
        elif conv.state.cancellation_type == "Deposit":
            return "This booking requires a deposit. Once the booking is complete, the user will receive an SMS asking for their credit card details to secure the booking. Ask if they would still like to proceed with the reservation. If they do, call temporary_lock_slot again with the same values."

    conv.state.table_type = selected_table_type
    conv.write_metric("REQUESTED_TABLE_TYPE", selected_table_type)

    api = get_restaurant_api(conv)
    experience_id = (
        conv.state.selected_experience.get("experience_id")
        if conv.state.selected_experience
        else None
    )
    data = {
        "restaurant_id": conv.variant.rid,
        "party_size": int(party_size),
        "date_time": parsed_datetime.strftime("%Y-%m-%dT%H:%M"),
        "table_type": conv.state.table_type,
        "experience_id": experience_id,
    }

    try:
        res = api.lock_booking(
            party_size=int(party_size),
            date_time=parsed_datetime.strftime("%Y-%m-%dT%H:%M"),
            table_type=conv.state.table_type,
            experience_id=experience_id,
        )
        if res.status_code == HTTPStatus.UNAUTHORIZED:
            plog.error("Invalid or expired token", response=res.text)
            return try_transfer_call(
                conv,
                "lock_slot_api_fail",
                "Hm, I’m having trouble making that booking. Let me put you through to someone who can help, one second.",
                "default",
            )

        if res.status_code == HTTPStatus.FORBIDDEN:
            plog.error("Authorization token is missing or invalid", response=res.text)
            return try_transfer_call(
                conv,
                "lock_slot_api_fail",
                "Hm, I’m having trouble making this booking. Let me put you through to someone who can help, one second.",
                "default",
            )

        if res.status_code in [HTTPStatus.BAD_REQUEST, HTTPStatus.NOT_FOUND]:
            error_data = res.json()
            for error in error_data.get("errors", []):
                code = error.get("code", "")
                if code == "NoAvailability":
                    return check_availability(
                        conv,
                        date=date,
                        time=time,
                        party_size=party_size,
                        selected_table_type=selected_table_type,
                    )
                if code == "MissingPartySize":
                    plog.error("Party size is missing", response=res.text, data=data)
                    return "The party size is required. Ask about the number of people again."
                if code == "InvalidPartySize":
                    plog.error("Invalid party size", response=res.text, data=data)
                    return "The party size is invalid. Ask about the number of people again."
                if code == "InvalidStartDateTime":
                    plog.error("Invalid start date/time", response=res.text, data=data)
                    return "You can only reserve slots that are at least 15 minutes after the current time. Ask about the date and time again."

        if not res.ok:
            plog.error("Unhandled error during reservation", response=res.text, data=data)
            return try_transfer_call(
                conv,
                "lock_slot_api_fail",
                "Hm, I’m having trouble making that booking. Let me put you through to someone who can help, one second.",
                "default",
            )

        response = res.json()
        if response:
            conv.write_metric("SLOT_LOCK_SUCCESSFUL")
            conv.state.availability_response = None
            conv.state.res_token = response.get("reservation_token")
            conv.state.origin_step = "Collect Customer Name"
            flow.goto_step("Collect Customer Name")
            if conv.state.include_experiences and (
                conv.state.standard_booking_selected or conv.state.selected_experience
            ):
                return {
                    "content": "You have temporarily reserved the slot, but in order to complete the booking, you will need to collect a few more details. You do not need to inform the user about this, but avoid telling them you have completed the booking or anything along those lines, just continue with the details collection as instructed.",
                    "utterance": "I'll go ahead with a standard reservation."
                    if not conv.state.selected_experience
                    else f"I'll go ahead with a reservation for {conv.state.selected_experience['name']}.",
                    "end_turn": False,
                }
            return "You have temporarily reserved the slot, but in order to complete the booking, you will need to collect a few more details. You do not need to inform the user about this, but avoid telling them you have completed the booking or anything along those lines, just continue with the details collection as instructed."

    except Exception as e:
        plog.error("Could not lock reservation slot", error=e, data=data)
        return try_transfer_call(
            conv,
            "lock_slot_api_fail",
            "Hm, I’m having trouble making this booking. Let me put you through to someone who can help, one second.",
            "default",
        )


def _payment_requirement_accepted(conv: Conversation, flow, date: str, time: str, party_size: int):
    if not conv.state.table_type_selection_enabled:
        return _temporarily_lock_slot(conv, flow, date, time, party_size, "default")
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

    conv.state.available_table_types = sorted(available_table_types & valid_table_types)
    if conv.state.available_table_types == ["default"]:
        return _temporarily_lock_slot(conv, flow, date, time, party_size, "default")
    available_types = ", ".join(
        "standard" if t == "default" else t for t in conv.state.available_table_types
    )
    flow.goto_step("Table type selection")
    if len(conv.state.available_table_types) == 1:
        return (
            f"The only available table type is {available_types}. "
            f"Ask the user if this is okay before going ahead. "
            f"If they agree, save '{conv.state.available_table_types[0]}' as selected_table_type. "
        )
    else:
        return (
            f"Multiple table types are available: {available_types}. "
            "Say 'standard' instead of 'default'. "
            "If the user selects 'standard', save 'default' as selected_table_type. "
            f"Only save one of these exact values: {', '.join(valid_table_types)}. "
            "If the user gives a synonym (e.g., 'indoors', 'outside seating'), map it to the closest valid value."
        )


def check_cancellation_policy(
    conv: Conversation,
    flow,
    datetime_str: str,
    experience_id: int,
    date,
    time,
    party_size,
):
    availability = conv.state.availability_response
    conv.state.cancellation_type = None
    if not experience_id:
        availability = filter_availability(availability, requested_type="Standard")
    else:
        availability = filter_availability(availability, requested_experience_id=experience_id)
    for time_available in availability.get("times_available", []):
        if time_available.get("time") == datetime_str:
            for availability_type in time_available.get("availability_types"):
                if cancellation_type := availability_type.get("cancellationPolicy", {}).get("type"):
                    conv.state.cancellation_type = cancellation_type
                for exp_cancellation_policy in availability_type.get(
                    "experienceCancellationPolicy", {}
                ):
                    if exp_cancellation_policy["experienceId"] == experience_id:
                        conv.state.cancellation_type = exp_cancellation_policy["type"]

    conv.write_metric(
        "BOOKING_CANCELLATION_POLICY",
        conv.state.cancellation_type.upper() if conv.state.cancellation_type else "NONE",
    )
    if conv.state.cancellation_type == "Deposit":
        flow.goto_step("Booking requires card details")
        return """This booking requires a deposit.
           If you have already informed user about the deposit policy, there is no need to give them any more information about it unless they specifically ask.
           Otherwise, inform them that once the booking is complete, they will receive an SMS asking for their credit card details to secure the booking - you cannot collect these over the phone (but no need to tell the last bit to the user).
           Ask if they would still like to go ahead with the reservation."""
    elif conv.state.cancellation_type == "Hold":
        flow.goto_step("Booking requires card details")
        return """This booking requires a credit card hold.
           If you have already informed user about the card hold policy, there is no need to give them any more information about it unless they specifically ask.
           Otherwise, inform them that once the booking is complete, they will receive an SMS asking for their credit card details to secure the booking - you cannot collect these over the phone (but no need to tell the last bit to the user).
           Ask if they would still like to go ahead with the reservation."""
    elif conv.state.cancellation_type == "Prepayment":
        # format total price
        price_info = conv.state.selected_experience.get("price_info", {})
        currency_code = price_info.get("currency_code")
        multiplier = price_info.get("multiplier")
        currency_names = {
            "USD": "dollars",
            "CAD": "dollars",
            "AUD": "dollars",
            "GBP": "pounds",
        }

        amount = conv.state.total_price / multiplier
        # Check if the amount is a whole number
        if amount.is_integer():
            amount_str = f"{int(amount)}"
        else:
            decimals = int(math.log10(multiplier))
            amount_str = f"{amount:.{decimals}f}"
        friendly_currency = currency_names.get(currency_code, currency_code)
        formatted_price = f"{amount_str} {friendly_currency}"
        conv.write_metric("PRE_PAYMENT_REQUIRED", write_once=True)
        flow.goto_step("Booking requires card details")
        return f"""This booking requires a pre-payment of {formatted_price}.
           If you have already informed user about the pre-payment policy, there is no need to give them any more information about it unless they specifically ask.
           Otherwise, inform them that once the booking is complete, they will receive an SMS asking for their credit card details to secure the booking - you cannot collect these over the phone (but no need to tell the last bit to the user).
           Ask if they would still like to go ahead with the reservation."""
    return _payment_requirement_accepted(conv, flow, date=date, time=time, party_size=party_size)
