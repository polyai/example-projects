from http import HTTPStatus

import plog
from _gen import *  # <AUTO GENERATED>
from functions.opentable_api import get_restaurant_api
from functions.try_transfer_call import try_transfer_call
from functions.write_booking_metric import write_booking_metric


@func_description(
    "Cancel an existing booking based on its specific ID. The ID can be retrieved by calling the get_bookings function."
)
@func_parameter("booking_id", "The ID of the booking to be cancelled")
@func_latency_control(
    delay_before_responses_start=0,
    silence_after_each_response=3,
    delay_responses=[("One moment please...", 3), ("Just a second...", 3)],
)
@plog.tmp_bind(api_integration="opentable")
def cancel_booking(conv: Conversation, booking_id: str):
    api = get_restaurant_api(conv)

    try:
        res = api.cancel_booking(booking_id)

        if res.status_code == HTTPStatus.UNAUTHORIZED:
            plog.error("Invalid or expired token", status_code=res.status_code, response=res.text)
            return try_transfer_call(
                conv,
                "cancel_booking_api_fail",
                "Hm, I’m having trouble cancelling that booking. Let me put you through to someone who can help, one second.",
                "default",
            )
        if res.status_code == HTTPStatus.FORBIDDEN:
            error_data = res.json()
            for error in error_data.get("errors", []):
                if error.get("code", "") == "RedirectToHost":
                    plog.error("Human intervention required", response=res.text)
                    return try_transfer_call(
                        conv,
                        "cancel_booking_requires_host",
                        "Hm, I’m having trouble cancelling that booking. Let me put you through to someone who can help, one second.",
                        "default",
                    )

            plog.error("Invalid or expired token", status_code=res.status_code, response=res.text)
            return try_transfer_call(
                conv,
                "cancel_booking_api_fail",
                "Hm, I’m having trouble cancelling that booking. Let me put you through to someone who can help, one second.",
                "default",
            )
        if res.status_code == HTTPStatus.BAD_REQUEST:
            error_data = res.json()
            for error in error_data.get("errors", []):
                if error.get("code", "") == "InvalidRidOrReservationId":
                    plog.error("Invalid restaurant ID or reservation ID", response=res.text)
                    return try_transfer_call(
                        conv,
                        "cancel_booking_api_fail",
                        "Hm, I’m having trouble cancelling that booking. Let me put you through to someone who can help, one second.",
                        "default",
                    )
        if not res.ok:
            plog.error(
                "Unhandled error during cancellation",
                status_code=res.status_code,
                response=res.text,
            )
            return try_transfer_call(
                conv,
                "cancel_booking_api_fail",
                "Hm, I’m having trouble cancelling that booking. Let me put you through to someone who can help, one second.",
                "default",
            )

        # metrics writing
        write_booking_metric(conv, "SUCCESSFUL_CANCEL", None, False)

        conv.state.origin_flow = None
        if conv.current_flow:
            conv.exit_flow()
        return "Booking successfully cancelled. Ask the user if there's anything you can help with."
    except Exception as e:
        plog.error("Could not cancel booking", error=e)
        return try_transfer_call(
            conv,
            "cancel_booking_api_fail",
            "Hm, I’m having trouble cancelling that booking. Let me put you through to someone who can help, one second.",
            "default",
        )
