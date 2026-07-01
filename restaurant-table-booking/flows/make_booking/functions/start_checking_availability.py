import ast
import datetime as dt

import plog
from _gen import *  # <AUTO GENERATED>
from functions.check_availability import (
    check_availability,
    check_availability_including_experiences,
)
from functions.start_handle_over_max_group_size import start_handle_over_max_group_size


def date_in_past(conv, date):
    current_date = dt.datetime.strptime(conv.state.current_date, "%A %d-%m-%Y").date()

    input_date = dt.datetime.strptime(date, "%Y-%m-%d").date()

    return input_date < current_date


def next_month_same_day(datestr):
    y, m, d = map(int, datestr.split("-"))
    if m == 12:
        ny, nm = y + 1, 1
    else:
        ny, nm = y, m + 1

    # clamp day to last day of next month if needed
    # last day of month: take first day of following month minus 1 day
    if nm == 12:
        first_following = dt.date(ny + 1, 1, 1)
    else:
        first_following = dt.date(ny, nm + 1, 1)

    last_day_next_month = (first_following - dt.timedelta(days=1)).day

    nd = min(d, last_day_next_month)
    return f"{ny:04d}-{nm:02d}-{nd:02d}"


@func_description(
    "Check if there are any tables available for at or around the requested date and time."
)
@func_parameter("party_size", "Party size for the booking")
@func_parameter("time", "Time of the requested booking slot in HH:MM format, e.g. 15:00")
@func_parameter(
    "date", "Date of the requested booking slot, which must be in the YYYY-MM-DD format"
)
@func_parameter(
    "selected_table_type",
    'Table type the caller chose from "default", "outdoor", "highTop", "bar", "counter", or "-" if unknown',
)
@func_parameter(
    "selected_experience_ids",
    'A list of all ids of experiences the user explicitly selected or strongly implied wanting to book for.  If no experiences were requested, this should be an empty list "[]", and if multiple are a match of user\'s preference, a list all matching entries e.g. "[123, 456]"',
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
def start_checking_availability(
    conv: Conversation,
    flow: Flow,
    party_size: int,
    time: str,
    date: str,
    selected_table_type: str,
    selected_experience_ids: str,
):
    conv.state.selected_experience = None

    plog.info("Test", test=conv._analytics_events)
    try:
        if int(party_size) >= int(conv.variant.large_party_size):
            return start_handle_over_max_group_size(conv, int(party_size))
        elif int(party_size) == 0:
            raise ValueError("Not a valid party size")
    except ValueError:
        return "You need to specify a party size. Ask the user if you don't know already."

    if date_in_past(conv, date):
        return f"""
    Since {date} is in the past, ask the user to confirm if they want to book a table on
     {next_month_same_day(date)}, then retry with the date they confirmed.
    """
    try:
        selected_experience_ids_list = (
            ast.literal_eval(selected_experience_ids) if selected_experience_ids else []
        )
        # If the result is a single integer, wrap it into a list so it's consistent
        if isinstance(selected_experience_ids_list, int):
            selected_experience_ids_list = [selected_experience_ids_list]
        # This filters out other types like strings, dicts, tuples, etc.
        if isinstance(selected_experience_ids_list, int):
            raise ValueError("selected_experience_ids must be a list.")
        if not all(isinstance(x, int) for x in selected_experience_ids_list):
            return "selected_experience_ids contains some non-integer values"
        for experience_id in selected_experience_ids_list:
            if experience_id not in conv.state.active_experiences:
                return f"{experience_id} in selected_experience_ids does not match any active experiences"
    except (ValueError, SyntaxError):
        return "selected_experience_ids is not a valid list."
    if not conv.state.include_experiences:
        if conv.state.table_type_selection_enabled:
            conv.state.origin_step = "Check availability - with table type"
            flow.goto_step("Check availability - with table type")
        else:
            conv.state.origin_step = "Check availability - no table type"
            flow.goto_step("Check availability - no table type")

        return check_availability(
            conv,
            date=date,
            time=time,
            party_size=party_size,
            selected_table_type=selected_table_type,
        )
    else:
        return check_availability_including_experiences(
            conv,
            flow,
            party_size,
            time,
            date,
            selected_table_type,
            selected_experience_ids_list,
        )
