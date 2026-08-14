from _gen import *  # <AUTO GENERATED>
import copy
import datetime as dt
from collections import defaultdict
from http import HTTPStatus
from typing import Optional
from zoneinfo import ZoneInfo

import plog
from functions.opentable_api import get_restaurant_api
from functions.start_handle_over_max_group_size import start_handle_over_max_group_size
from functions.try_transfer_call import is_restaurant_ooh, try_transfer_call

valid_table_types = {"default", "outdoor", "highTop", "bar", "counter"}


def check_cancellation_policy(conv, datetime_str: str):
    conv.state.need_to_check_cancellation_policy = False
    response = conv.state.availability_response

    for time_available in response.get("times_available", []):
        if time_available.get("time") == datetime_str:
            requested_availability_type = "Standard"
            conv.state.cancellation_type = (
                next(
                    (
                        at
                        for at in time_available.get("availability_types", [])
                        if at.get("type") == requested_availability_type
                    ),
                    {},
                )
                .get("cancellationPolicy", {})
                .get("type")
            )
            conv.write_metric(
                "BOOKING_CANCELLATION_POLICY",
                conv.state.cancellation_type.upper()
                if conv.state.cancellation_type
                else "NONE",
            )
            return


def get_hours_for_date(conv, date: dt.date):
    """Return the hours string for a given date, checking special dates first."""
    date_str = date.isoformat()
    if special := conv.state.special_dates.get(date_str):
        plog.info(f"special_date: {special}")
        if special.get("closed"):
            return None
        return special.get("hours")
    weekday = date.strftime("%A")
    return conv.state.site_opening_hours.get(weekday)


def handle_restaurant_closed(
    conv: Conversation, date_str: str, booking_type: str, time_str: Optional[str] = None
):
    """Return a message if the restaurant is closed on the given date/time, else None."""
    hours_today = get_hours_for_date(conv, dt.date.fromisoformat(date_str))

    special_date = conv.state.special_dates.get(date_str)
    if special_date:
        special_date_reason = special_date.get("reason", "")
        conv.state.special_date_hours = special_date.get("hours")

        if conv.state.special_date_hours.lower() == "closed":
            conv.write_metric(
                f"{booking_type.upper()}_BOOKING_RESTAURANT_CLOSED",
                None,
                write_once=True,
            )
            reason_msg = f" due to {special_date_reason}" if special_date_reason else ""
            return f"The restaurant is closed on {date_str}{reason_msg}. Could you try another date for your booking?"

    if time_str and not is_time_in_hours(conv, date_str, time_str):
        conv.write_metric(
            f"{booking_type.upper()}_RESTAURANT_CLOSED", True, write_once=True
        )
        return f"The restaurant is open {hours_today}. Could you try another time?"

    opening_hours = get_hours_for_date(conv, dt.datetime.fromisoformat(date_str).date())
    if not opening_hours or opening_hours.lower() == "closed":
        conv.write_metric(
            f"{booking_type.upper()}_RESTAURANT_CLOSED", None, write_once=True
        )
        return f"The restaurant is closed on {date_str}. Could you try another date?"

    return None


def is_time_in_hours(conv, date_str, time_str):
    """Return True if the given date/time falls within restaurant hours."""
    if "T" in time_str:
        dt_obj = dt.datetime.fromisoformat(time_str)
    else:
        date_part = dt.datetime.fromisoformat(date_str).date()
        time_part = dt.datetime.strptime(time_str, "%H:%M").time()
        dt_obj = dt.datetime.combine(date_part, time_part)
    return not is_restaurant_ooh(conv, dt_obj, use_only_opening_hours=True)


def filter_slots_by_hours(conv, slots, date_str):
    """Filter a list of times_available dicts so that only slots within hours remain."""
    return [slot for slot in slots if is_time_in_hours(conv, date_str, slot["time"])]


def sort_times_by_proximity(conv, time_strings: list, reference_dt):
    """Sort ISO time strings by proximity to reference_dt, filtering out past times."""
    if not time_strings:
        return []

    parsed_times = []
    for ts in time_strings:
        try:
            parsed_times.append(dt.datetime.fromisoformat(ts))
        except Exception:
            return time_strings

    now = dt.datetime.now(ZoneInfo(conv.variant.timezone)).replace(tzinfo=None)
    grace_time = now + dt.timedelta(minutes=15)
    parsed_times = [t for t in parsed_times if t > grace_time]

    def sort_key(datetime_obj):
        diff = abs((datetime_obj - reference_dt).total_seconds() / 60)
        is_before = 1 if datetime_obj < reference_dt else -1
        return (diff, is_before)

    return [t.isoformat() for t in sorted(parsed_times, key=sort_key)]


def round_to_nearest_quarter(dt_obj):
    """Round datetime to the nearest 15-minute interval."""
    discard = dt_obj.minute % 15
    minute = dt_obj.minute - discard if discard < 8 else dt_obj.minute + (15 - discard)
    rounded = dt_obj.replace(minute=0, second=0, microsecond=0) + dt.timedelta(
        minutes=minute
    )
    if rounded.minute == 60:
        rounded = rounded.replace(minute=0) + dt.timedelta(hours=1)
    return rounded


def round_up_to_next_quarter(dt_obj):
    """Round datetime up to the next 15-minute interval."""
    if dt_obj.minute % 15 == 0 and dt_obj.second == 0 and dt_obj.microsecond == 0:
        return dt_obj
    return dt_obj.replace(minute=0, second=0, microsecond=0) + dt.timedelta(
        minutes=((dt_obj.minute // 15) + 1) * 15
    )


def get_nearest_possible_booking_time(conv, input_dt):
    """Return the nearest bookable 15-min slot, at least 15 min from now."""
    now = dt.datetime.now(ZoneInfo(conv.variant.timezone)).replace(tzinfo=None)
    grace_time = now + dt.timedelta(minutes=15)
    input_dt_rounded = round_to_nearest_quarter(input_dt)
    if input_dt_rounded >= grace_time:
        return input_dt_rounded
    return round_up_to_next_quarter(grace_time)


def filter_availability(
    data, requested_table_type=None, requested_experience_id=None, requested_type=None
):
    """Filter availability response by table type, experience, or availability type."""
    new_data = copy.deepcopy(data)
    filtered_times_available = []

    for time_entry in data["times_available"]:
        new_availability_types = []
        for availability in time_entry["availability_types"]:
            if requested_type and availability["type"] != requested_type:
                continue
            new_dining_areas = [
                area
                for area in availability["diningArea"]
                if (
                    not requested_table_type
                    or requested_table_type in area.get("table_type", [])
                )
                and (
                    not requested_experience_id
                    or requested_experience_id in area.get("experience_ids", [])
                )
            ]
            if new_dining_areas:
                new_availability_types.append(
                    {**availability, "diningArea": new_dining_areas}
                )
        if new_availability_types:
            filtered_times_available.append(
                {
                    "time": time_entry["time"],
                    "availability_types": new_availability_types,
                }
            )

    new_data["times_available"] = filtered_times_available
    valid_times = {entry["time"] for entry in filtered_times_available}
    new_data["times"] = [t for t in new_data["times"] if t in valid_times]
    return new_data


def handle_check_availability_error(conv, res, params):
    """Handle API error responses from the availability endpoint."""
    if res.status_code in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
        plog.error(
            "Auth error during availability check", response=res.text, data=params
        )
        return try_transfer_call(
            conv,
            "check_availability_api_fail",
            "Hm, I'm having trouble checking availability for this booking. Let me put you through to someone who can help, one second.",
            "default",
        )

    if res.status_code == HTTPStatus.BAD_REQUEST:
        error_data = res.json()
        for error in error_data.get("errors", []):
            code = error.get("code", "")
            if code == "InvalidPartySize":
                plog.error("Invalid party size", response=res.text, data=params)
                return (
                    "The party size is invalid. Ask about the number of people again."
                )
            if code == "MissingPartySize":
                plog.error(
                    "Missing party size in request", response=res.text, data=params
                )
                return (
                    "The party size is required. Ask about the number of people again."
                )
            if code in ("InvalidDateTime", "MissingDateTime"):
                plog.error(f"{code}", response=res.text, data=params)
                return "The date or time provided is invalid. Ask about the date and time again."
            if code == "InvalidStartDateTime":
                plog.error("Invalid start date/time", response=res.text, data=params)
                return "You can only search for slots 15 minutes after the current time. Ask about the date and time again."
            if code in ("InvalidForwardMinutes", "InvalidBackwardMinutes"):
                plog.error(f"{code}", response=res.text, data=params)
                return try_transfer_call(
                    conv,
                    "check_availability_api_fail",
                    "Hm, I'm having trouble checking availability for this booking. Let me put you through to someone who can help, one second.",
                    "default",
                )

    plog.error(
        "Unhandled error during availability check", response=res.text, data=params
    )
    return try_transfer_call(
        conv,
        "check_availability_api_fail",
        "Hm, I'm having trouble checking availability for this booking. Let me put you through to someone who can help, one second.",
        "default",
    )


@func_description(
    "Check if the restaurant has a free table for the requested number of people, date and time. Do not assume what the user wants. Always ask explicitly how many people and what time the booking is for."
)
@func_parameter(
    "date",
    'Date of the requested booking slot, which must be in the YYYY-MM-DD format, or "-" if unknown',
)
@func_parameter(
    "time",
    'Time of the requested booking slot in HH:MM format, e.g. 15:00, or "-" if unknown',
)
@func_parameter("party_size", 'Party size for the booking, or "-" if unknown')
@func_parameter(
    "selected_table_type",
    'Table type the caller chose from "default", "outdoor", "highTop", "bar", "counter", or "-" if unknown',
)
@func_latency_control(
    delay_before_responses_start=0,
    silence_after_each_response=7,
    delay_responses=[
        ("Let me just check what space we have...", 3),
        ("One more moment...", 2),
        ("Sorry, this is taking a bit longer", 3),
    ],
)
@plog.tmp_bind(api_integration="opentable")
def check_availability(
    conv: Conversation, date: str, time: str, party_size: int, selected_table_type: str
):
    try:
        if int(party_size) >= int(conv.variant.large_party_size):
            return start_handle_over_max_group_size(conv, int(party_size))
        elif int(party_size) == 0:
            raise ValueError("Not a valid party size")
    except ValueError:
        return (
            "You need to specify a party size. Ask the user if you don't know already."
        )

    if date in ["today", "tomorrow"]:
        return "Error: You did not provide a valid date. Please try again."

    parsed_date = None
    try:
        parsed_date = dt.date.fromisoformat(date)
    except ValueError as e:
        if str(e) == "day is out of range for month":
            return "The day is out of range for the month. Ask for a different date."
    if not parsed_date:
        return (
            "The date you provided was in the wrong format. If you know the date requested by the user, "
            "please try calling this function again using the following format: YYYY-MM-DD. "
            "Otherwise, ask the user what day they would like to book."
        )

    parsed_time = None
    try:
        parsed_time = dt.time.fromisoformat(time)
    except ValueError:
        pass
    if not parsed_time:
        return (
            "The time you provided was in the wrong format. If you know the time requested by the user, "
            "please try calling this function again using the following format: HH:MM. "
            "Otherwise, ask the user what time they would like to book."
        )

    datetime_obj = dt.datetime.combine(parsed_date, parsed_time)
    if datetime_obj < dt.datetime.now(ZoneInfo(conv.variant.timezone)).replace(
        tzinfo=None
    ) - dt.timedelta(hours=1):
        return (
            "The date and time provided is in the past. For times on or after midnight, the user might "
            "actually want to be using e.g. 'today at 1am' to refer to a date that is actually tomorrow. "
            "If that's the case here, you can just call this function again with the corrected date."
        )

    adjusted_datetime_str = get_nearest_possible_booking_time(
        conv, datetime_obj
    ).strftime("%Y-%m-%dT%H:%M")
    conv.state.requested_date = datetime_obj.strftime("%d/%m/%Y")
    conv.state.requested_time = datetime_obj.strftime("%H:%M")
    conv.state.requested_party_size = party_size

    # Write metrics
    conv.write_metric("ORIGINAL_DATE", datetime_obj.strftime("%Y/%m/%d"))
    conv.write_metric("ORIGINAL_TIME", datetime_obj.strftime("%H:%M"))
    conv.write_metric("BOOKING_COVER", party_size)
    if selected_table_type in valid_table_types:
        conv.write_metric("REQUESTED_TABLE_TYPE", selected_table_type)

    # Check if restaurant is closed
    flow_type = "CREATE" if conv.current_flow == "make_booking" else "AMEND"
    if closed_prompt := handle_restaurant_closed(conv, date, flow_type, time):
        return closed_prompt

    api = get_restaurant_api(conv)
    params = {
        "party_size": int(party_size),
        "start_date_time": adjusted_datetime_str,
        "forward_minutes": 180,
        "backward_minutes": 180,
    }

    try:
        res = api.check_availability(
            party_size=int(party_size),
            date_time=adjusted_datetime_str,
            forward_minutes=180,
            backward_minutes=180,
        )
        if not res.ok:
            return handle_check_availability_error(conv, res, params)

        response = res.json()
        plog.info("Get availability response", response=response)
        if not conv.state.table_type_selection_enabled:
            response = filter_availability(response, requested_table_type="default")
            plog.info("Get availability response (filtered)", response=response)

        # No time available within 3 hours -- scan the whole day
        no_time_available_within_3_hours = False
        if not response.get("times"):
            no_time_available_within_3_hours = True
            for scan_time in (dt.time(3), dt.time(9), dt.time(15), dt.time(21)):
                scan_dt = dt.datetime.combine(parsed_date, scan_time)
                scan_adj = get_nearest_possible_booking_time(conv, scan_dt).strftime(
                    "%Y-%m-%dT%H:%M"
                )
                res = api.check_availability(
                    party_size=int(party_size),
                    date_time=scan_adj,
                    forward_minutes=180,
                    backward_minutes=180,
                )
                if not res.ok:
                    return handle_check_availability_error(conv, res, params)
                scan_resp = res.json()
                if not conv.state.table_type_selection_enabled:
                    scan_resp = filter_availability(
                        scan_resp, requested_table_type="default"
                    )
                response["times"].extend(scan_resp.get("times", []))
                response["times_available"].extend(scan_resp.get("times_available", []))

        response["times_available"] = filter_slots_by_hours(
            conv, response.get("times_available", []), date
        )
        response["times"] = [slot["time"] for slot in response["times_available"]]
        conv.state.availability_response = response

        if available_times := response.get("times"):
            if adjusted_datetime_str in available_times:
                if conv.current_flow == "make_booking":
                    conv.write_metric("REQUESTED_SLOT_AVAILABLE")
                else:
                    conv.write_metric("AMEND_REQUESTED_TIME_AVAILABLE")

                # Table type logic
                table_type_to_times = defaultdict(list)
                for slot in response.get("times_available", []):
                    ts = slot.get("time")
                    if not ts:
                        continue
                    for avail in slot.get("availability_types", []):
                        if avail.get("type") != "Standard":
                            continue
                        for area in avail.get("diningArea", []):
                            for ttype in area.get("table_type", []):
                                if ttype in valid_table_types:
                                    table_type_to_times[ttype].append(ts)

                for time_available in response.get("times_available", []):
                    if time_available.get("time") == adjusted_datetime_str:
                        table_types = set()
                        for avail in time_available.get("availability_types", []):
                            if avail.get("type") != "Standard":
                                continue
                            for area in avail.get("diningArea", []):
                                for ttype in area.get("table_type", []):
                                    table_types.add(ttype)

                        conv.state.available_table_types = sorted(
                            table_types & valid_table_types
                        )
                        conv.state.needs_table_type_confirmation = (
                            conv.state.table_type_selection_enabled
                            and (
                                table_types != {"default"}
                                or selected_table_type not in ["default", "-"]
                            )
                            and conv.current_flow == "make_booking"
                        )

                        if conv.state.needs_table_type_confirmation:
                            available_types = ", ".join(
                                "standard" if t == "default" else t
                                for t in conv.state.available_table_types
                            )
                            table_type_availability = sort_times_by_proximity(
                                conv,
                                table_type_to_times[selected_table_type],
                                datetime_obj,
                            )
                            if len(conv.state.available_table_types) == 1:
                                return (
                                    f"There is a table available at {adjusted_datetime_str}. "
                                    f"The only available table type is {available_types}. "
                                    f"Ask the user if this is okay before going ahead. "
                                    f"If they agree, save '{conv.state.available_table_types[0]}' as selected_table_type. "
                                    f"If they say they would prefer another table type (e.g., indoor, outdoor, bar, etc.), "
                                    f"Suggest to them the next available time for the table type they want from '{table_type_availability}' remembering that indoors/inside is referring to a 'default' table. "
                                )
                            return (
                                f"There is a table available at {adjusted_datetime_str}. "
                                f"Multiple table types are available: {available_types}. "
                                "Say 'standard' instead of 'default'. "
                                "If the user selects 'standard', save 'default' as selected_table_type. "
                                f"Only save one of these exact values: {', '.join(valid_table_types)}. "
                                "If the user gives a synonym (e.g., 'indoors', 'outside seating'), map it to the closest valid value."
                            )

                extra_notes = ""
                if (
                    selected_table_type not in ["-", "default"]
                    and not conv.state.table_type_selection_enabled
                ):
                    conv.state.saved_table_type = selected_table_type
                    extra_notes += f" This is not necessarilly a {selected_table_type}, so make sure to not reference that in your response. Instead, say 'Please note that while we'll do our best, {selected_table_type} seating is first-come, first-served and can't be guaranteed. Would you like to go ahead?'"
                check_cancellation_policy(conv, adjusted_datetime_str)

                if (
                    conv.state.cancellation_type == "Hold"
                    and conv.current_flow == "make_booking"
                ):
                    return (
                        f"There is a table available at {adjusted_datetime_str}, but it requires a credit card hold. "
                        "If you have already informed user about the card hold policy, there is no need to give them any more information about it unless they specifically ask. "
                        "Otherwise, inform them that once the booking is complete, they will receive an SMS asking for their credit card details to secure the booking - you cannot collect these over the phone (but no need to tell the last bit to the user). "
                        f"Ask if they would still like to go ahead with the reservation. If they agree, use 'default' as selected_table_type.{extra_notes}"
                    )
                if (
                    conv.state.cancellation_type == "Deposit"
                    and conv.current_flow == "make_booking"
                ):
                    return (
                        f"There is a table available at {adjusted_datetime_str}, but it requires a deposit. "
                        "If you have already informed user about the deposit policy, there is no need to give them any more information about it unless they specifically ask. "
                        "Otherwise, inform them that once the booking is complete, they will receive an SMS asking for their credit card details to secure the booking - you cannot collect these over the phone (but no need to tell the last bit to the user). "
                        f"Ask if they would still like to go ahead with the reservation. If they agree, use 'default' as selected_table_type.{extra_notes}"
                    )
                return f"There is a table available at the {adjusted_datetime_str}. Ask the user if they would like to go ahead with the reservation. If they agree, use 'default' as selected_table_type.{extra_notes}"
            else:
                if no_time_available_within_3_hours:
                    conv.write_metric("FULLY_BOOKED_ALT_SUGGESTED")
                if conv.current_flow == "make_booking":
                    conv.write_metric("SUGGESTED_CLOSEST_AVAILABLE_TIME")
                else:
                    conv.write_metric("AMEND_SUGGESTED_CLOSEST_AVAILABLE_TIME")
                conv.state.need_to_check_cancellation_policy = True
                return (
                    f"The requested time is not available, but here are some alternatives: {sort_times_by_proximity(conv, available_times, datetime_obj)}. "
                    "Pick the first time and offer it as the nearest available time to the user. If the user refuses it, offer the next time. Keep in mind to offer at most 2 alernatives.\n"
                    "# EXAMPLE CONVERSATION:\n"
                    "AGENT: We don't have any tables free at 5pm tomorrow, the nearest available slot we have is 6pm, would that work for you?\n"
                    "USER: No\n"
                    "AGENT: We also have space earlier at 3pm, would that be better?\n"
                    "USER: No\n"
                    "AGENT: Is there another date or time I could check for you?"
                )

        if conv.current_flow == "make_booking":
            conv.write_metric("FULLY_BOOKED")
        else:
            conv.write_metric("AMEND_FULLY_BOOKED")
        return f"Tell user that you don't have any free tables all day on {parsed_date.strftime('%A %d %B')} (avoid mentioning the time, as you did check the wholde day). Ask if there is another day that you can check for them."

    except Exception as e:
        plog.error("Could not check availability", error=e, data=params)
        return try_transfer_call(
            conv,
            "check_availability_api_fail",
            "Hm, I'm having trouble checking availability for this booking. Let me put you through to someone who can help, one second.",
            "default",
        )


def check_availability_including_experiences(
    conv: Conversation,
    flow,
    party_size: int,
    time: str,
    date: str,
    selected_table_type: str,
    selected_experience_ids: list,
):
    """Thin wrapper for callers that pass experience IDs.

    Experiences are not supported in the template, so this delegates directly
    to check_availability, ignoring the experience parameters.
    """
    return check_availability(
        conv,
        date=date,
        time=time,
        party_size=party_size,
        selected_table_type=selected_table_type,
    )
