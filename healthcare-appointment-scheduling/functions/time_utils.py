import datetime as dt
from zoneinfo import ZoneInfo

from _gen import *  # <AUTO GENERATED>

# --- CUSTOMIZE: Set your Poly Clinic timezone and hours ---
CLINIC_TIMEZONE = "America/New_York"
OPENING_TIME = dt.time(8, 0, 0)
CLOSING_TIME = dt.time(17, 0, 0)


def set_datetime(conv: Conversation):
    def ordinal_suffix(day):
        if 11 <= day <= 13:
            return f"{day}th"
        return f"{day}{'st' if day % 10 == 1 else 'nd' if day % 10 == 2 else 'rd' if day % 10 == 3 else 'th'}"

    now = dt.datetime.now(ZoneInfo(CLINIC_TIMEZONE))
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


def is_ooh_clinic(conv: Conversation) -> bool:
    """
    OOH check for Poly Clinic.
    Default hours: Mon-Fri 8:00 AM - 5:00 PM.
    Weekends: closed.
    """
    now = dt.datetime.now(ZoneInfo(CLINIC_TIMEZONE))
    weekday = now.weekday()

    if weekday >= 5:
        return True

    return not (OPENING_TIME <= now.time() < CLOSING_TIME)


@func_description(
    "[Utils] Utility functions for current time and out-of-hours behavior"
)
def time_utils(conv: Conversation):
    pass
