import datetime as dt
from zoneinfo import ZoneInfo

from _gen import *  # <AUTO GENERATED>


def set_datetime(conv: Conversation):
    def ordinal_suffix(day):
        if 11 <= day <= 13:
            return f"{day}th"
        else:
            return f"{day}{'st' if day % 10 == 1 else 'nd' if day % 10 == 2 else 'rd' if day % 10 == 3 else 'th'}"

    now = dt.datetime.now(ZoneInfo("America/New_York"))  # set the timezone for project
    # now = dt.datetime.now(ZoneInfo(conv.variant.timezone))  # alternatively, read the timezone from variant
    conv.state.now = now
    conv.state.current_date = now.strftime("%A %d-%m-%Y")
    conv.state.current_weekday = now.strftime("%A")
    conv.state.current_time = now.strftime("%H:%M")
    conv.state.formatted_date_time = now.strftime("%A, %B %d, %Y at %I:%M %p")
    conv.state.next_few_days = "\n".join(
        [
            (now + dt.timedelta(days=i)).strftime(
                f" - %A {ordinal_suffix((now + dt.timedelta(days=i)).day)} of %B %Y"
            )
            for i in range(1, 7)
        ]
    )


def is_ooh(conv: Conversation):
    DAY_NAME_TO_INDEX = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }

    def parse_time(hms: str):
        h, m, s = map(int, hms.split(":"))
        return dt.time(h, m, s)

    if conv.variant:
        now = dt.datetime.now(ZoneInfo(conv.variant.timezone))
    else:
        now = dt.datetime.now(ZoneInfo("America/New_York"))  # set the correct timezone

    flags = conv.real_time_config.get("flags", {})
    if not isinstance(flags, dict):
        raise Exception("real_time_config flags are not a dict")
    if flags.get("ooh_forced"):
        return True
    if not flags.get("ooh_enabled"):
        return False

    today = now.date()
    weekday = now.weekday()

    # special hours override
    special_hours = conv.real_time_config.get("special_hours")
    if not isinstance(special_hours, list):
        raise Exception("real_time_config special_hours are not a list")
    for sh in special_hours:
        if sh["date"] == today.isoformat():
            return not sh.get("is_open", False)

    # regular hours
    regular_hours = conv.real_time_config.get("regular_hours")
    if not isinstance(regular_hours, list):
        raise Exception("real_time_config regular_hours are not a list")
    for rh in regular_hours:
        if DAY_NAME_TO_INDEX[rh["day_of_week"].lower()] == weekday:
            if not rh.get("is_open", False):
                return True
            start = parse_time(rh["opening"])
            end = parse_time(rh["closing"])
            return not (start <= now.time() < end)

    # no matching rule = closed
    return True


# Mortgage-specific in-hours times
MORTAGES_NEW_APP_IN_HOURS_TIMES = {
    0: (9, 0, 17, 30),  # Mon 9:00 to 17:30
    1: (10, 0, 17, 30),  # Tue 10:00 to 17:30
    2: (9, 0, 17, 30),  # Wed 9:00 to 17:30
    3: (9, 0, 17, 30),  # Thu 9:00 to 17:30
    4: (9, 0, 17, 30),  # Fri 9:00 to 17:30
    5: (0, 0, 0, 0),  # Sat closed
    6: (0, 0, 0, 0),  # Sun closed
}

MORTAGES_NEW_IN_HOURS_TIMES = {
    0: (9, 0, 17, 30),  # Mon 9:00 to 17:30
    1: (9, 0, 17, 30),  # Tue 09:00 to 17:30
    2: (9, 0, 17, 30),  # Wed 9:00 to 17:30
    3: (10, 0, 17, 30),  # Thu 10:00 to 17:30
    4: (9, 0, 17, 30),  # Fri 9:00 to 17:30
    5: (0, 0, 0, 0),  # Sat closed
    6: (0, 0, 0, 0),  # Sun closed
}

MORTAGES_EXISTING_IN_HOURS_TIMES = {
    0: (8, 30, 18, 00),  # Mon 8:30 to 18:00
    1: (8, 30, 18, 00),  # Tue 8:30 to 18:00
    2: (8, 30, 18, 00),  # Wed 8:30 to 18:00
    3: (8, 30, 18, 00),  # Thu 8:30 to 18:00
    4: (8, 30, 18, 00),  # Fri 8:30 to 18:00
    5: (0, 0, 0, 0),  # Sat closed
    6: (0, 0, 0, 0),  # Sun closed
}

MORTGAGES_QUEUE_TO_HOURS = {
    "Mortgages Application In Process": MORTAGES_NEW_APP_IN_HOURS_TIMES,
    "Mortgages New Application": MORTAGES_NEW_IN_HOURS_TIMES,
    "Mortgages Financial Difficulty": MORTAGES_EXISTING_IN_HOURS_TIMES,
    "Mortgages Existing General": MORTAGES_EXISTING_IN_HOURS_TIMES,
    "Mortgages Broker": MORTAGES_NEW_IN_HOURS_TIMES,
}


def is_mortgage_queue_ooh(conv: Conversation, queue_name: str) -> bool:
    """
    Check if a specific mortgage queue is out of hours based on mortgage-specific times.

    Args:
        conv: The conversation object
        queue_name: The name of the mortgage queue to check

    Returns:
        True if the queue is out of hours, False if in hours
    """
    if queue_name not in MORTGAGES_QUEUE_TO_HOURS:
        # If not a mortgage queue, fall back to regular OOH check
        return is_ooh(conv)

    if conv.variant:
        now = dt.datetime.now(ZoneInfo(conv.variant.timezone))
    else:
        now = dt.datetime.now(ZoneInfo("America/New_York"))

    weekday = now.weekday()
    hours = MORTGAGES_QUEUE_TO_HOURS[queue_name]

    # Get hours for current weekday
    day_hours = hours.get(weekday, (0, 0, 0, 0))
    start_hour, start_min, end_hour, end_min = day_hours

    # If all zeros, queue is closed (OOH)
    if start_hour == 0 and start_min == 0 and end_hour == 0 and end_min == 0:
        return True

    # Check if current time is within hours
    start_time = dt.time(start_hour, start_min)
    end_time = dt.time(end_hour, end_min)
    current_time = now.time()

    # Return True if outside hours (OOH)
    return not (start_time <= current_time < end_time)


@func_description("[Utils] Utility functions for current time and out-of-hours behavior")
def time_utils(conv: Conversation):
    pass
