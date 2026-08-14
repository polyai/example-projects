from _gen import *  # <AUTO GENERATED>
from datetime import datetime, time
from zoneinfo import ZoneInfo


@func_description("check if the call is within call center hours")
def in_hours(conv: Conversation):
    # Get configuration
    config = conv.real_time_config
    opening_hours = config.get("opening_hours", {})
    timezone_str = config.get("timezone", "US/Central")

    conv.log.info(
        "Configuration loaded",
        config_keys=list(config.keys()) if config else [],
        opening_hours_keys=list(opening_hours.keys()) if opening_hours else [],
        timezone=timezone_str,
    )

    # Check if out-of-hours is force enabled
    if config.get("settings", {}).get("force_ooh_enabled", False):
        conv.log.info("Force OOH enabled")
        return False

    if not opening_hours:
        conv.log.error("opening_hours configuration is missing", full_config=config)
        # Default to out of hours if config is missing
        return False

    try:
        timezone = ZoneInfo(timezone_str)
    except Exception as e:
        conv.log.error(
            "Invalid timezone in config", timezone=timezone_str, error=str(e)
        )
        timezone = ZoneInfo("US/Central")

    call_center_datetime = conv.state.datetime_now.astimezone(timezone)

    # Map weekday to config key
    weekday_map = {
        0: "monday",
        1: "tuesday",
        2: "wednesday",
        3: "thursday",
        4: "friday",
        5: "saturday",
        6: "sunday",
    }

    # Check for special dates first (holidays, etc.)
    special_dates = opening_hours.get("special_dates", [])
    current_date = call_center_datetime.date().isoformat()

    hours_str = None
    for special_date in special_dates:
        if special_date.get("date") == current_date:
            hours_str = special_date.get("hours")
            conv.log.info(
                "Using special date hours",
                date=current_date,
                special_date_name=special_date.get("special_date_name"),
                hours=hours_str,
            )
            break

    # If no special date, use weekday schedule
    if hours_str is None:
        weekday_key = weekday_map.get(call_center_datetime.weekday())
        hours_str = opening_hours.get(weekday_key, "closed")
        conv.log.info(
            "Using regular weekday hours", weekday=weekday_key, hours=hours_str
        )

    # Parse hours string
    if hours_str.lower() in ["closed", "close"]:
        conv.log.info("Call center is closed for whole day")
        return False

    # Parse HH:MM-HH:MM format
    try:
        start_time_str, end_time_str = hours_str.split("-")
        start_hour, start_minute = map(int, start_time_str.split(":"))
        end_hour, end_minute = map(int, end_time_str.split(":"))

        start_time = datetime.combine(
            call_center_datetime.date(), time(hour=start_hour, minute=start_minute)
        ).replace(tzinfo=timezone)

        end_time = datetime.combine(
            call_center_datetime.date(), time(hour=end_hour, minute=end_minute)
        ).replace(tzinfo=timezone)

        current_time = conv.state.datetime_now.astimezone(timezone)

        is_open = start_time <= current_time < end_time

        conv.log.info(
            "Hours check result",
            current_time=current_time.isoformat(),
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            is_open=is_open,
        )

        return is_open

    except Exception as e:
        conv.log.error(
            "Failed to parse hours string", hours_str=hours_str, error=str(e)
        )
        # Default to out of hours if parsing fails
        return False
