"""Texting a link: the questions to ask, shared by start_send_text and send_text.

With a usable caller ID the caller is asked whether to send it to the number
they're calling from, without reading it out. Any other number is read back
digit by digit before it's texted. The turn each question is asked in is kept,
so a yes in that same turn sends nothing.
"""

from _gen import *  # <AUTO GENERATED>
from functions import bookings, idnv

ASKED_KEY = "sms"
CALLING_QUESTION = "Shall I send it to the number you're calling from?"
NUMBER_ASK = "What number should I send it to?"
MOBILE_ASK = "What's the best mobile number to send it to?"
SENT_CALLING = "I've sent the link over to you now."
SENT_OTHER = "I've sent the link to that number now."
ANYTHING_ELSE = "Is there anything else I can help with?"


@func_description("[UTIL] Text helpers, not callable directly")
def texts(conv: Conversation):
    return "Text helpers module."


def number_sentence(digits: str) -> str:
    return f"That's {idnv.spell_phone(digits)}. Shall I send it there?"


def ask_number(conv, digits: str) -> str:
    """Read a number back, then ask whether to text it."""
    bookings.mark_asked(conv, ASKED_KEY)
    return (
        f'Say: "Sure. {number_sentence(digits)}" A yes, or an acknowledgement to that question '
        '("okay", "sure"), is a yes: call send_text with number_confirmed=\'true\'. A corrected '
        "number: call send_text with it."
    )


def ask_calling_number(conv) -> str:
    """Ask whether to text the number they're calling from, never saying it."""
    bookings.mark_asked(conv, ASKED_KEY)
    return (
        f'Ask: "{CALLING_QUESTION}" Never say the number. A yes, or an acknowledgement to that '
        "question, is a yes: call send_text with use_calling_number='true'. No: ask "
        f'"{NUMBER_ASK}" and call send_text with the number they give.'
    )


def ask_mobile() -> str:
    return (
        f'Ask: "{MOBILE_ASK}" Then call send_text with it. If they have no mobile, say where to '
        "find it instead, from the topic, and don't send anything."
    )
