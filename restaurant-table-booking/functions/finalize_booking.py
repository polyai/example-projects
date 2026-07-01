from datetime import datetime
from http import HTTPStatus

import plog
from _gen import *  # <AUTO GENERATED>
from functions.opentable_api import get_restaurant_api
from functions.try_transfer_call import try_transfer_call
from functions.write_booking_metric import write_booking_metric


@func_description(
    "Finalize the booking for a customer, using the details provided in the conversation. If some details are unknown, the user will need to be asked to provide them."
)
@func_parameter(
    "booking_notes",
    "summary of any special requirements - also look at all the previous user inputs and figure out if anything's relevant here",
)
@func_parameter(
    "dietary_requirements",
    "If user specified dietary requirements (do NOT ask user about these explicitly, but do add them in booking_notes if user tells them to you unprompted)",
)
@func_latency_control(
    delay_before_responses_start=0,
    silence_after_each_response=2,
    delay_responses=[("One moment while I complete the booking...", 3), ("One more moment...", 2)],
)
@plog.tmp_bind(api_integration="opentable")
def finalize_booking(conv: Conversation, booking_notes: str, dietary_requirements: bool):
    # Check that the necessary previous steps were done
    # if not conv.state.first_name_confirmed:
    #   return """You need to call save_first_name with the latest name information before you can proceed with making a reservation.
    #   If you haven't asked the user for their name yet, do this now.
    #   Otherwise, call save_first_name with the latest information. You will not be able to make a booking until you call that function."""

    experience = None
    if experience := conv.state.selected_experience:
        experience = {
            "id": experience["experience_id"],
            "version": experience["version"],
            "party_size_per_price_type": conv.state.party_size_per_price_type,
        }

    api = get_restaurant_api(conv)
    data = {
        "first_name": conv.state.first_name_spelling,
        "last_name": conv.state.last_name_spelling,
        "phone_number": conv.state.phone_number,
        "reservation_token": conv.state.res_token,
    }

    try:
        res = api.finalize_booking(
            first_name=conv.state.first_name_spelling.capitalize(),
            last_name=conv.state.last_name_spelling.capitalize(),
            phone_number=conv.state.phone_number.removeprefix("0"),
            country_code=conv.state.country_code,
            reservation_token=conv.state.res_token,
            special_request=booking_notes if booking_notes != "-" else None,
            table_type=conv.state.table_type,
            experience=experience,
        )

        if res.status_code == HTTPStatus.UNAUTHORIZED:
            plog.error(
                "Invalid or expired token",
                status_code=res.status_code,
                response=res.text,
                data=data,
            )
            return try_transfer_call(
                conv,
                "make_booking_api_fail",
                "Hm, I'm having trouble making this booking. Let me put you through to someone who can help, one second.",
                "default",
            )

        if res.status_code == HTTPStatus.FORBIDDEN:
            plog.error(
                "Authorization token is missing or invalid",
                status_code=res.status_code,
                response=res.text,
                data=data,
            )
            return try_transfer_call(
                conv,
                "make_booking_api_fail",
                "Hm, I'm having trouble making this booking. Let me put you through to someone who can help, one second.",
                "default",
            )

        if res.status_code == HTTPStatus.BAD_REQUEST:
            error_data = res.json()
            for error in error_data.get("errors", []):
                code = error.get("code", "")
                if code == "FirstNameIsMissing":
                    plog.error("First name is missing", response=res.text, data=data)
                    return "The user's first name is required. Ask for the first name again."
                if code == "LastNameIsMissing":
                    plog.error("Last name is missing", response=res.text, data=data)
                    return "The user's last name is required. Ask for the last name again."
                if code == "IllegalPhoneNumber":
                    plog.error("Invalid phone number", response=res.text, data=data)
                    if conv.state.invalid_phone_number:
                        return try_transfer_call(
                            conv,
                            "make_booking_api_fail",
                            "Hm, I'm having trouble making this booking. Let me put you through to someone who can help, one second.",
                            "default",
                        )
                    conv.state.invalid_phone_number = True
                    conv.state.additional_booking_final_details = "Immediately call the save_phone_number_and_move_on function with the new phone number if the booking couldn't be finalized because the phone number is invalid"
                    return "The phone number provided is invalid."
                if code == "ReservationTokenOrRidInvalid":
                    plog.error(
                        "Invalid reservation token or restaurant ID", response=res.text, data=data
                    )
                    return try_transfer_call(
                        conv,
                        "make_booking_api_fail",
                        "Hm, I'm having trouble making this booking. Let me put you through to someone who can help, one second.",
                        "default",
                    )
                if code == "InvalidStartDateTime":
                    plog.error("Invalid start date/time", response=res.text, data=data)
                    return try_transfer_call(
                        conv,
                        "make_booking_in_the_past",
                        "Hm, I'm having trouble making this booking. Let me put you through to someone who can help, one second.",
                        "default",
                    )
                if code == "RestaurantNotSCEnabled":
                    plog.error("Restaurant is not SCC enabled", response=res.text, data=data)
                    return "This restaurant cannot process payments or credit card holds. Inform the user that bookings are not possible at this time."

        if res.status_code == HTTPStatus.NOT_FOUND:
            error_data = res.json()
            for error in error_data.get("errors", []):
                if error.get("code", "") == "NoAvailability":
                    plog.error("No availability found", response=res.text, data=data)
                    return "No availability found for the requested time. Ask the user for another time or date."

        if not res.ok:
            plog.error(
                "Unhandled error during booking",
                status_code=res.status_code,
                response=res.text,
                data=data,
            )
            return try_transfer_call(
                conv,
                "make_booking_api_fail",
                "Hm, I'm having trouble making this booking. Let me put you through to someone who can help, one second.",
                "default",
            )

        # Handle successful booking
        response = res.json()
        conv.state.booking = response
        party_size = response["party_size"]
        date_time = datetime.strptime(response["date_time"], "%Y-%m-%dT%H:%M")
        date = date_time.date()
        time = date_time.time()

        # Write metrics
        if conv.state.had_successful_booking:
            write_booking_metric(conv, "BOOKING_SUCCESSFUL_MULTIPLE", None, True)
        else:
            write_booking_metric(conv, "SUCCESSFUL_BOOKING", None, True)
        write_booking_metric(conv, "SUCCESSFUL_BOOKING_DATE", date.strftime("%Y/%m/%d"), False)
        write_booking_metric(conv, "SUCCESSFUL_BOOKING_TIME", time.strftime("%H:%M"), False)
        write_booking_metric(conv, "SUCCESSFUL_BOOKING_COVERS", party_size, False)
        write_booking_metric(
            conv,
            "SUCCESSFUL_BOOKING_CANCELLATION_POLICY",
            conv.state.cancellation_type.upper() if conv.state.cancellation_type else "NONE",
            False,
        )
        if experience:
            conv.write_metric(
                "BOOKED_EXPERIENCE_NAME", value=conv.state.selected_experience_name, write_once=True
            )
        conv.state.had_successful_booking = True
        conv.state.origin_flow = None
        conv.state.origin_step = None
        conv.exit_flow()

        if conv.state.cancellation_type == "Hold":
            output = f"Provisionally booked table for {party_size} people for {conv.state.first_name_spelling.capitalize()}, {time}, {date}. Remind the user that they will need to provide their credit card details using the link in the SMS they will now receive to secure their booking. Remind the user to do this as soon as possible to ensure their booking is locked in."
        elif conv.state.cancellation_type == "Deposit":
            output = f"Provisionally booked table for {party_size} people for {conv.state.first_name_spelling.capitalize()}, {time}, {date}. Remind the user that they will need to pay a deposit using the link in the SMS they will now receive to secure their booking. Remind the user to do this as soon as possible to ensure their booking is locked in."
        if conv.state.make_multiple_bookings:
            output = f"Successfully booked a table for {date} for {party_size} people. Confirm the booking and ask if they would like to make another booking with the same booking detials"
        else:
            output = f"Successfully booked table for {party_size} people for {conv.state.first_name_spelling.capitalize()}, {time}, {date}. Confirm the booking and say 'Is there anything else I can assist you with today?'."

        if dietary_requirements:
            output = (
                output
                + " "
                + (
                    "Remind the user to let their server know of their dietary requirement on the day."
                )
            )

        return output

    except Exception as e:
        plog.error("Could not make booking", error=e, data=data)
        return try_transfer_call(
            conv,
            "make_booking_api_fail",
            "Hm, I'm having trouble making this booking. Let me put you through to someone who can help, one second.",
            "default",
        )
