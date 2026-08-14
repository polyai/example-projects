import datetime as dt

from _gen import *  # <AUTO GENERATED>


def get_hours_string(site_hours):
    result = []
    if not site_hours:
        return ""
    for day, hours in site_hours.items():
        hours = hours.strip().lower()
        if not hours or hours == "closed":
            result.append(f"{day}: closed")
            continue

        parts = []
        for interval in hours.split(";"):
            interval = interval.strip()
            shift_split = interval.split("-")
            open_time = shift_split[0]
            close_time = shift_split[-1]
            if open_time == "00:00":
                open_time = "midnight"
            if close_time == "00:00":
                close_time = "midnight"
            parts.append(f"{open_time} - {close_time}")
        result.append(f"{day}: {'; '.join(parts)}")
    return "; ".join(result)


@func_description("Get the opening hours for a specific date or day of the week.")
@func_parameter(
    "date", 'Specific date to get the hours for, in a YYYY-MM-DD format (or "-")'
)
@func_parameter(
    "day_of_the_week",
    'General day of the week to get the hours for, e.g. "Monday" or "Saturday" (or "-")',
)
def get_opening_hours(conv: Conversation, date: str, day_of_the_week: str):
    opening_hours = conv.state.site_opening_hours or {}

    extra_prompt = (
        "All times are in 24-hour format (01:00 is 1 AM, 13:00 is 1 PM). "
        "Convert to 12-hour format before responding. "
        "If the caller only asks about closing or opening times, only give that time."
    )

    if date == "-" and day_of_the_week == "-":
        return (
            f"Our opening hours are: {get_hours_string(opening_hours)}. {extra_prompt}"
        )

    if date and conv.state.special_dates and conv.state.special_dates.get(date):
        special = conv.state.special_dates[date]
        hours = special.get("hours")
        reason = special.get("reason")
        return f"Special date hours for {date}: {hours}, say {reason} if there is one. {extra_prompt}"

    day_key = None
    if date:
        try:
            parsed_date = dt.date.fromisoformat(date)
            day_key = parsed_date.strftime("%A")
        except ValueError:
            pass
    elif day_of_the_week:
        day_key = day_of_the_week.capitalize()

    if day_key:
        hours = opening_hours.get(day_key, "not available")
        return f"Opening hours for {day_key}: {hours}. {extra_prompt}"

    return "The provided arguments could not be interpreted as a valid date or day of the week. Please try again."
