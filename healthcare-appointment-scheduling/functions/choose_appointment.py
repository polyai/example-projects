from _gen import *  # <AUTO GENERATED>
from functions import appointments
from functions.handoff import handoff

TRIES = 2
NOT_PICKED_UTTERANCE = (
    "I'm sorry, I can't tell which appointment you mean. Let me put you through to our "
    "scheduling team, one moment please."
)


@func_description(
    "The caller has several upcoming appointments and has said which one they mean. Pass its date, its type, or both."
)
@func_parameter(
    "appointment_date",
    "The date of the appointment they mean, as YYYY-MM-DD. Empty if not said.",
)
@func_parameter(
    "appointment_type",
    "The type they named, as one of 'Sick visit', 'Follow-up' or 'Wellness check': pick the one that fits what they said (a recheck is a Follow-up). Empty if not said.",
)
def choose_appointment(
    conv: Conversation, appointment_date: str, appointment_type: str
):
    appt = appointments.choose(conv, appointment_date, appointment_type)
    if not appt:
        misses = int(conv.state.choose_misses or 0) + 1
        conv.state.choose_misses = misses
        if misses >= TRIES:
            conv.state.choose_misses = 0
            return handoff(conv, "SCHEDULING", NOT_PICKED_UTTERANCE)
        listing = "; ".join(
            appointments.describe(a, conv) for a in appointments.upcoming(conv)
        )
        return (
            f"NOT ONE APPOINTMENT (attempt {misses} of {TRIES}). Their appointments: {listing}. "
            "Ask which one they mean, by its day or its type. Then call choose_appointment again "
            "with whatever they say, even if it's the same as before."
        )
    conv.state.choose_misses = 0
    task = conv.state.task
    described = appointments.describe(appt, conv)
    if task == "cancel":
        from flows.cancel_appointment.functions.cancel_appointment import (
            cancel_readback,
        )

        return cancel_readback(conv)
    if task == "reschedule":
        return f"They mean {described}. Ask when would suit them instead, unless they've said."
    return f"Read the appointment back in one natural sentence: {described}. Then ask if there's anything else."
