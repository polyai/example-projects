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


def parse_opening_hours(conv):
    opening_hours = conv.variant.opening_hours.split("\n")
    opening_hours_dict = {}
    for line in opening_hours:
        if line:
            key, value = line.split(":", 1)
            opening_hours_dict[key.strip().capitalize()] = value.strip()
    return opening_hours_dict


@func_description("Get the opening hours for a specific date or day of the week.")
@func_parameter("date", 'Specific date to get the hours for, in a YYYY-MM-DD format (or "-")')
@func_parameter(
    "day_of_the_week",
    'General day of the week to get the hours for, e.g. "Monday" or "Saturday" (or "-")',
)
def get_opening_hours(conv: Conversation, date: str, day_of_the_week: str):
    hours_types = {
        "opening hours": conv.state.site_opening_hours or {},
        "kitchen hours": conv.state.site_kitchen_hours or conv.state.site_opening_hours,
        "bar hours": conv.state.site_bar_hours or conv.state.site_opening_hours,
    }

    formatting_prompt = f"""
Our regular opening hours are: {get_hours_string(conv.state.site_opening_hours)}.
Our kitchen hours are: {get_hours_string(conv.state.site_kitchen_hours)}.
Our bar hours are: {get_hours_string(conv.state.site_bar_hours)}.
All times are in 24-hour format (01:00 is 1 AM, 02:00 is 2 AM, 13:00 is 1 PM etc). When reasoning, first carefully convert times to 12 hour format before forming the final response: e.g. 11:30-02:00 is 11:30 AM to 2:00 AM.If the caller asks about a specific type of hours (kitchen, bar, opening), give them that time.
If you don't know hours for specific type, say regular opening hours. List each day and its hours.
"""

    extra_prompt = """
All times are in 24-hour format (01:00 is 1 AM, 02:00 is 2 AM, 13:00 is 1 PM etc). When reasoning, first carefully convert times to 12 hour format before forming the final response: e.g. 11:30-02:00 is 11:30 AM to 2:00 AM.
If the caller asks about a specific type of hours (kitchen, bar, opening), give them that time. If that type of hours is not specified for the day/date, say the regular opening hours for that day.
If the caller only asks about closing or opening times then ONLY give that time for example if the caller asks what time the restaurant closes on Fridays, DO NOT give opening time as well, only closing time.
If a caller asks "what time do you open for breakfast on Sundays" then you can assume they want the opening time and you can say "we open for breakfast at..." and then give them the time.
"""
    result = {}

    if date == "-" and day_of_the_week == "-":
        return f"{hours_types}. {formatting_prompt}"

    if date and conv.state.special_dates and conv.state.special_dates.get(date):
        special = conv.state.special_dates[date]
        hours = special.get("hours")
        reason = special.get("reason")
        return (
            f"Special date hours for {date}: {hours}, say {reason} if there is one. {extra_prompt}"
        )

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
        for ht, hours_dict in hours_types.items():
            result[ht] = hours_dict.get(day_key)
        return f"Opening hours for {day_key} ({date or 'unknown date'}): {result}. {extra_prompt}"

    return "The provided arguments could not be interpreted as a valid date or day of the week. Please try again."
