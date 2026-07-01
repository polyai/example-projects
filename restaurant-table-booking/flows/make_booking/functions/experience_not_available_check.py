import ast

from _gen import *  # <AUTO GENERATED>
from functions.check_availability import check_availability_including_experiences


@func_description("If the user requests an experience which is not available proceed to this step")
@func_parameter("party_size", "Party size for the booking")
@func_parameter(
    "time", 'Time of the requested booking slot in HH:MM format, e.g. 15:00, or "-" if unknown'
)
@func_parameter(
    "date",
    'Date of the requested booking slot, which must be in the YYYY-MM-DD format, or "-" if unknown',
)
@func_parameter(
    "selected_table_type",
    'Table type the caller chose from "default", "outdoor", "highTop", "bar", "counter", or "-" if unknown',
)
@func_parameter(
    "selected_experience_ids",
    'A list of all ids of experiences the user explicitly selected or strongly implied wanting to book for.  If no experiences were requested, this should be an empty list "[]", and if multiple are a match of user\'s preference, a list all matching entries e.g. "[123, 456]"',
)
def experience_not_available_check(
    conv: Conversation,
    flow: Flow,
    party_size: int,
    time: str,
    date: str,
    selected_table_type: str,
    selected_experience_ids: str,
):
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
    return check_availability_including_experiences(
        conv, flow, party_size, time, date, selected_table_type, selected_experience_ids_list
    )
