from _gen import *  # <AUTO GENERATED>
from datetime import datetime


@func_description(
    "Checks if the date the user mentioned exists. This is used when the LLM is not sure if the date exists."
)
@func_parameter("date", "Mentioned date, in a YYYY-MM-DD format")
@func_latency_control(
    delay_before_responses_start=0,
    silence_after_each_response=6,
    delay_responses=[("$check_if_date_exists_delay_utterance", 2)],
)
def check_if_date_exists(conv: Conversation, date: str):
    conv.state.check_if_date_exists_delay_utterance = ""
    try:
        # Parse the input string
        year, month, day = map(int, date.split("-"))

        # Get the day with proper ordinal suffix
        if 10 <= day % 100 <= 20:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")

        # Basic validation for month
        month_names = {
            1: "January",
            2: "February",
            3: "March",
            4: "April",
            5: "May",
            6: "June",
            7: "July",
            8: "August",
            9: "September",
            10: "October",
            11: "November",
            12: "December",
        }

        if month < 1 or month > 12:
            return f"Month {month} does not exist"

        month_name = month_names[month]

        # Try to create the date (this will raise ValueError if day is invalid)
        try:
            date_obj = datetime(year, month, day)
            # Get the day of the week
            day_of_week = date_obj.strftime("%A")
            return f"{day}{suffix} of {month_name} exists, and it's on a {day_of_week}. Now continue with the conversation."
        except ValueError:
            return f"{day}{suffix} of {month_name} does not exist"

    except Exception:
        return "Something is wrong with the date"
