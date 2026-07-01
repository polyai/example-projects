import datetime as dt
from http import HTTPStatus

import plog
from _gen import *  # <AUTO GENERATED>
from functions.opentable_api import get_restaurant_api
from functions.start_handle_over_max_group_size import start_handle_over_max_group_size
from functions.try_transfer_call import try_transfer_call
from functions.write_booking_metric import write_booking_metric


@func_description(
    'Edit an existing booking based on its specific ID. The ID can be retrieved by calling the get_bookings function. Fields that should not be updated should have the following value: "-".'
)
@func_parameter("booking_id", "The ID of the booking to be cancelled")
@func_parameter("new_partysize", "Updated number of people the booking is for")
@func_parameter("new_time", "Updated time of the booking (formatted as HH:MM, e.g. 18:00, 11:00)")
@func_parameter("new_date", "Updated date of the booking (must be in the YYYY-MM-DD format)")
@func_parameter("booking_notes", "Updated booking notes")
@func_latency_control(
    delay_before_responses_start=0,
    silence_after_each_response=3,
    delay_responses=[
        ("One moment please while I change that...", 2),
        ("Just a second...", 1),
        ("One more moment...", 2),
    ],
)
@plog.tmp_bind(api_integration="opentable")
def modify_booking(
    conv: Conversation,
    booking_id: str,
    new_partysize: int,
    new_time: str,
    new_date: str,
    booking_notes: str,
):
    # Validate the values
    if new_partysize != "-" and int(new_partysize) >= int(conv.variant.large_party_size):
        return start_handle_over_max_group_size(conv, int(new_partysize))

    current_booking_datetime = dt.datetime.fromisoformat(conv.state.booking.get("date_time"))
    # Format to desired formats
    parsed_date = None
    try:
        if not new_date or new_date == "-":
            parsed_date = current_booking_datetime.date()
        else:
            parsed_date = dt.date.fromisoformat(new_date)
    except ValueError:
        pass
    if new_date != "-" and not parsed_date:
        return """The date you provided was in the wrong format. If you know the date requested by the user, please try again
    using the following format: YYYY-MM-DD"""

    parsed_time = None
    try:
        if not new_time or new_time == "-":
            parsed_time = current_booking_datetime.time()
        else:
            parsed_time = dt.time.fromisoformat(new_time)
    except ValueError:
        pass
    if new_time != "-" and not parsed_time:
        return """The time you provided was in the wrong format. If you know the time requested by the user, please try again
    using the following format: 11:00"""

    parsed_datetime = dt.datetime.combine(parsed_date, parsed_time)
    api = get_restaurant_api(conv)
    data = {
        "party_size": new_partysize,
        "date_time": parsed_datetime.strftime("%Y-%m-%dT%H:%M"),
        "special_request": booking_notes if booking_notes != "-" else None,
    }

    try:
        res = api.modify_booking(
            booking_id=booking_id,
            party_size=new_partysize,
            date_time=parsed_datetime.strftime("%Y-%m-%dT%H:%M"),
            special_request=booking_notes if booking_notes != "-" else None,
        )

        if res.status_code == HTTPStatus.UNAUTHORIZED:
            plog.error("Invalid or expired token", response=res.text, data=data)
            return try_transfer_call(
                conv,
                "make_booking_api_fail",
                "Hm, I’m having trouble changing that booking. Let me put you through to someone who can help, one second.",
                "default",
            )

        if res.status_code == HTTPStatus.FORBIDDEN:
            error_data = res.json()
            for error in error_data.get("errors", []):
                if error.get("code", "") == "RedirectToHost":
                    plog.error("Human intervention required", response=res.text)
                    return try_transfer_call(
                        conv,
                        "update_booking_requires_host",
                        "Hm, I’m having trouble changing that booking. Let me put you through to someone who can help, one second.",
                        "default",
                    )
            plog.error("Invalid or expired token", response=res.text, data=data)
            return try_transfer_call(
                conv,
                "update_booking_api_fail",
                "Hm, I’m having trouble changing that booking. Let me put you through to someone who can help, one second.",
                "default",
            )

        if res.status_code == HTTPStatus.BAD_REQUEST:
            error_data = res.json()
            for error in error_data.get("errors", []):
                code = error.get("code", "")
                if code == "MissingPartySize":
                    plog.warning("Invalid party size.", response=res.text)
                    return "The party size is invalid. Ask about the number of people again."
                if code == "InvalidRidOrReservationId":
                    plog.error("Invalid restaurant ID or reservation ID", response=res.text)
                    return try_transfer_call(
                        conv,
                        "update_booking_api_fail",
                        "Hm, I’m having trouble changing that booking. Let me put you through to someone who can help, one second.",
                        "default",
                    )
                if code == "InvalidDateTime":
                    plog.error("Invalid date or time", response=res.text)
                    return (
                        "The date or time provided is invalid. Ask about the date and time again."
                    )
                if code == "InvalidStartDateTime":
                    plog.warning("Invalid start date/time", response=res.text)
                    return "You can only book slots which are 15 minutes after the current time at the restaurant. Ask about the date and time again."
                if code == "CannotModifyReservationInPast":
                    plog.error("Cannot modify reservation in past", response=res.text, data=data)
                    return try_transfer_call(
                        conv,
                        "update_booking_in_past",
                        "Hm, I’m having trouble changing that booking. Let me put you through to someone who can help, one second.",
                        "default",
                    )

        if not res.ok:
            plog.error("Unhandled error during modification", response=res.text, data=data)
            return try_transfer_call(
                conv,
                "update_booking_api_fail",
                "Hm, I’m having trouble changing that booking. Let me put you through to someone who can help, one second.",
                "default",
            )

        # Write metrics
        write_booking_metric(conv, "SUCCESSFUL_AMEND", None, False)
        write_booking_metric(
            conv, "SUCCESSFUL_AMEND_DATE", parsed_datetime.strftime("%Y/%m/%d"), False
        )
        write_booking_metric(
            conv, "SUCCESSFUL_AMEND_TIME", parsed_datetime.strftime("%H:%M"), False
        )
        write_booking_metric(conv, "SUCCESSFUL_AMEND_COVERS", new_partysize, False)
        conv.state.booking = res.json()
        conv.state.origin_flow = None
        if conv.current_flow:
            conv.exit_flow()
        return "Booking successfully updated"

    except Exception as e:
        plog.error("Could not modify booking", error=e)
        return try_transfer_call(
            conv,
            "update_booking_api_fail",
            "Hm, I’m having trouble changing that booking. Let me put you through to someone who can help, one second.",
            "default",
        )
