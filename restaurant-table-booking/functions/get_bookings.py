from http import HTTPStatus

import plog
from _gen import *  # <AUTO GENERATED>
from functions.opentable_api import get_restaurant_api


@func_description("Get the detail of all bookings made with a given phone number")
@func_parameter(
    "phone_number",
    "Phone number that the booking was made under (national significant number). If there are dashes, spaces or leading zeros, make sure to remove them.",
)
@func_parameter(
    "country_code", 'country code, without leading + (assume UK if not given, i.e. "44")'
)
@plog.tmp_bind(api_integration="opentable")
def get_bookings(conv: Conversation, phone_number: str, country_code: str):
    api = get_restaurant_api(conv)
    data = {
        "phone": {
            "number": phone_number.removeprefix("0"),
            "country_code": int(country_code),
        },
    }

    res = api.get_bookings(
        phone_number=phone_number.removeprefix("0"),
        country_code=country_code,
    )

    if res.status_code == HTTPStatus.NOT_FOUND:
        return []
    if res.status_code in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
        plog.error("Invalid or expired token", response=res.text, data=data)
        return None
    if res.status_code == HTTPStatus.BAD_REQUEST:
        error_data = res.json()
        for error in error_data.get("errors", []):
            if error.get("code", "") in {"IllegalPhoneNumber", "MissingPhoneNumber"}:
                plog.warning(
                    "Invalid phone number or missing phone entity",
                    response=res.text,
                    data=data,
                )
                return []
    if not res.ok:
        plog.error("Unhandled API error", response=res.text, data=data)
        return None

    # Parse the response
    json_res = res.json()
    bookings = []
    if "reservations" in json_res:
        response_bookings = json_res["reservations"]
        if not response_bookings:
            bookings = []
        elif not isinstance(response_bookings, list):
            bookings = [response_bookings]
        else:
            bookings = response_bookings

    conv.state.user_bookings = bookings
    return bookings
