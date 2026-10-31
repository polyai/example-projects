from _gen import *  # <AUTO GENERATED>
from functions.utils import HOURS_NOT_TO_HAND, site_hours_utterance


@func_description(
    "Call this function when the user asks about business hours or when the office is open."
)
def handle_business_hours_faq(conv: Conversation):
    hours = site_hours_utterance(conv)

    if hours:
        return f"Tell the caller our hours: {hours} Then carry on with anything you were in the middle of."

    return (
        f'Say: "{HOURS_NOT_TO_HAND}" Don\'t give or guess any times. Then carry on with '
        "anything you were in the middle of."
    )
