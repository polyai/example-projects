from _gen import *  # <AUTO GENERATED>
from functions.store_info import attr
from functions.utils import (
    hours_not_to_hand,
    opening_hours_utterance,
    variant_opening_hours,
)


@func_description(
    "Get this store's opening hours. Call it whenever the caller asks when the store is open."
)
def get_opening_hours(conv: Conversation):
    hours = opening_hours_utterance(variant_opening_hours(conv))
    if hours:
        return f"This store's hours: {hours} Give only the hours they asked about, in words."
    say = hours_not_to_hand(conv)
    offer = (
        " Offer to text the website link; if they say yes, call start_send_sms with "
        "sms_id='website'."
        if attr(conv, "website_url")
        else ""
    )
    return f'Say: "{say}" Don\'t guess or give any times.{offer}'
