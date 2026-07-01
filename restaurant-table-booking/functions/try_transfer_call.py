from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from _gen import *  # <AUTO GENERATED>


def build_transfer_configs(conv):
    weekdays_map = {
        "01_monday": "Monday",
        "02_tuesday": "Tuesday",
        "03_wednesday": "Wednesday",
        "04_thursday": "Thursday",
        "05_friday": "Friday",
        "06_saturday": "Saturday",
        "07_sunday": "Sunday",
    }

    # Get list of ooh transfers
    ooh_transfers = conv.real_time_config.get("ooh_transfers", [])

    # Build dictionary keyed by transfer type
    transfer_configs = {}
    for transfer in ooh_transfers:
        transfer_type = transfer.get("00_type")
        if not transfer_type:
            continue

        raw_oh = transfer.get("04_opening_hours", {})

        # Build flattened opening_hours dictionary
        opening_hours = {}

        # Change weekday keys to weekday with capitalization (e.g. "01_monday" -> "Monday")
        for day in [
            "01_monday",
            "02_tuesday",
            "03_wednesday",
            "04_thursday",
            "05_friday",
            "06_saturday",
            "07_sunday",
        ]:
            if day in raw_oh:
                weekday = weekdays_map[day]
                opening_hours[weekday.capitalize()] = raw_oh[day]

        # Extract special_dates array and add entries by date string
        special_dates = raw_oh.get("08_special_dates", [])
        for special in special_dates:
            date = special.get("date")
            hours = special.get("hours")
            if date and hours:
                opening_hours[date] = hours

        transfer_configs[transfer_type] = {
            "use_site_opening_hours": transfer.get("03_use_site_opening_hours", True),
            "ooh_message": transfer.get(
                "02_ooh_message",
                "Okay, we're currently closed but you can leave a voicemail and a member of the team will get back to you as soon as possible. One moment while I transfer you.",
            ),
            "transfer_ooh": transfer.get("01_transfer_ooh", True),
            "opening_hours": opening_hours,
            "timezone": raw_oh.get("04_opening_hours", {}).get("00_timezone")
            or conv.variant.timezone,
        }

    return transfer_configs


def is_restaurant_ooh(conv, current_dt, use_only_opening_hours=False):
    # Check festive hours first
    if conv.state.site_staffed_hours and not use_only_opening_hours:
        rest_hours = conv.state.site_staffed_hours
    else:
        rest_hours = conv.state.site_opening_hours
    current_time = current_dt.time()

    date_today = current_dt.date()
    date_yesterday = (current_dt - timedelta(days=1)).date()

    # Check for Special Dates
    today_str = date_today.isoformat()
    if today_str in conv.state.special_dates:
        special_date_hours = conv.state.special_dates[today_str].get("hours")
        if special_date_hours == "closed":
            return True
        rest_hours = {today_str: special_date_hours}

    hours_today = rest_hours.get(date_today.isoformat())
    if not hours_today:
        hours_today = rest_hours.get(date_today.strftime("%A").capitalize())

    hours_yesterday = rest_hours.get(date_yesterday.isoformat())
    if not hours_yesterday:
        hours_yesterday = rest_hours.get(date_yesterday.strftime("%A").capitalize())

    # Determine if the site is within hours
    if hours_today:
        if hours_today.strip().lower() != "closed":
            shifts = hours_today.split(";")
            for shift in shifts:
                shift_split = shift.split("-")
                open_str = shift_split[0]
                close_str = shift_split[-1]
                open_time = time.fromisoformat(open_str.strip())
                close_time = time.fromisoformat(close_str.strip())

                # shift ends after midnight
                if close_time <= open_time and open_time <= current_time:
                    return False
                # normal opening hours
                if current_time >= open_time and current_time <= close_time:
                    return False
    if hours_yesterday:
        if hours_yesterday.strip().lower() != "closed":
            shifts = hours_yesterday.split(";")
            for shift in shifts:
                shift_split = shift.split("-")
                open_str = shift_split[0]
                close_str = shift_split[-1]
                open_time = time.fromisoformat(open_str.strip())
                close_time = time.fromisoformat(close_str.strip())

                # shift ends after midnight
                if close_time <= open_time and current_time <= close_time:
                    return False
    return True


def is_destination_ooh(conv, destination, transfer_configs):
    # Check festive hours first
    dest_hours = transfer_configs[destination]["opening_hours"]
    current_dt = datetime.now(ZoneInfo(transfer_configs[destination]["timezone"]))
    current_time = current_dt.time()

    date_today = current_dt.date()
    hours_today = dest_hours.get(date_today.isoformat())
    if not hours_today:
        hours_today = dest_hours.get(date_today.strftime("%A").capitalize())

    date_yesterday = (current_dt - timedelta(days=1)).date()
    hours_yesterday = dest_hours.get(date_yesterday.isoformat())
    if not hours_yesterday:
        hours_yesterday = dest_hours.get(date_yesterday.strftime("%A").capitalize())

    # Determine if the destination is within hours
    if hours_today:
        if hours_today.strip().lower() != "closed":
            shifts = hours_today.split(";")
            for shift in shifts:
                shift_split = shift.split("-")
                open_str = shift_split[0]
                close_str = shift_split[-1]
                open_time = time.fromisoformat(open_str.strip())
                close_time = time.fromisoformat(close_str.strip())

                # shift ends after midnight
                if close_time <= open_time and open_time <= current_time:
                    return False
                # normal opening hours
                if current_time >= open_time and current_time <= close_time:
                    return False
    if hours_yesterday:
        if hours_yesterday.strip().lower() != "closed":
            shifts = hours_yesterday.split(";")
            for shift in shifts:
                shift_split = shift.split("-")
                open_str = shift_split[0]
                close_str = shift_split[-1]
                open_time = time.fromisoformat(open_str.strip())
                close_time = time.fromisoformat(close_str.strip())

                # shift ends after midnight
                if close_time <= open_time and current_time <= close_time:
                    return False
    return True


@func_description(
    "Check if a call can be transferred (i.e. if it's in hours) and either says handoff_utterance and transfers call, or proposes an alternative solution to the user."
)
@func_parameter("handoff_reason", "identifier of why call is being handed off")
@func_parameter(
    "handoff_utterance",
    "the handoff utterance to be said if checks in this function are successful",
)
@func_parameter(
    "handoff_to",
    'handoff destination, use "default" unless you have been explicitly told otherwise in instructions',
)
def try_transfer_call(
    conv: Conversation, handoff_reason: str, handoff_utterance: str, handoff_to: str
):
    default_transfer_destination = conv.real_time_config.get("default_transfer", "STANDARD")
    transfer_configs = build_transfer_configs(conv)
    if handoff_reason == "speak_to_human":
        number_of_turns_in_conv = len([turn for turn in conv.history if turn.role == "user"])
        if number_of_turns_in_conv == 1:
            return {
                "utterance": "I might be able to help you myself. I can make, amend or cancel bookings and I can also answer questions. Could you tell me what you need?",
                "content": "If user asks to speak to a human again or says 'no', call try_transfer_call again with the same parameters.",
            }
    now = datetime.now(ZoneInfo(conv.variant.timezone))
    skip_ooh = False
    if handoff_to == "FORCE_STANDARD_HANDOFF":
        skip_ooh = True
        handoff_to = "STANDARD"
    if nbr := conv.variant.get(f"transfer_number_{handoff_to}"):
        transfer_number = nbr
    else:
        handoff_to = default_transfer_destination
        transfer_number = conv.variant.get(f"transfer_number_{handoff_to}")

    is_ooh = True
    if transfer_configs[handoff_to]["use_site_opening_hours"]:
        is_ooh = is_restaurant_ooh(conv, now)
    else:
        is_ooh = is_destination_ooh(conv, handoff_to, transfer_configs)
        # return f"Else {is_ooh}"

    if is_ooh and not skip_ooh:
        # This function might get called from a flow, so make sure to exit the flow only
        # if the agent is inside one, otherwise `conv.exit_flow()` will crash the agent
        # if conv.current_flow is not None:
        #   conv.exit_flow()
        handoff_utterance = transfer_configs[handoff_to]["ooh_message"]
        if not transfer_configs[handoff_to]["transfer_ooh"]:
            if conv.current_flow:
                conv.exit_flow()
            return f"Say: '{handoff_utterance}' and ask user if there is anything else you can help them with."
    return {
        "utterance": handoff_utterance,
        "handoff": {
            "type": handoff_to,
            "reason": handoff_reason,
            "refer": {"phone_number": transfer_number},
        },
    }
