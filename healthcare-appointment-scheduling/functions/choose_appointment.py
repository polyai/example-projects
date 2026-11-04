from _gen import *  # <AUTO GENERATED>
from functions import appointments
from functions.handoff import handoff

TRIES = 2
NOT_PICKED_UTTERANCE = (
    "I'm sorry, I can't tell which appointment you mean. I'll put you through to our "
    "scheduling team, who can help. One moment, please."
)


@func_description(
    "The caller has several upcoming appointments and has said which one they mean. Pass its date, its type, or both."
)
@func_parameter(
    "appointment_date", "The date of the appointment they mean, as YYYY-MM-DD."
)
@func_parameter(
    "appointment_type",
    "Its type, as 'Sick visit', 'Follow-up' or 'Wellness check', from what they said.",
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
            return handoff(conv, "APPOINTMENT_NOT_PICKED", NOT_PICKED_UTTERANCE)
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
        return appointments.cancel_readback(conv)
    if task == "reschedule":
        return (
            f"APPOINTMENT: {described}. Say it in a few words (\"That's your "
            f'{appointments.kind(appt["type"])} {appointments.on_date(appt["date"], appointments.today(conv))}.")'
            ' and, unless they\'ve said, ask "When would suit you instead?"'
        )
    return (
        f'APPOINTMENT: {described}. Say it in one natural sentence ("That\'s {described}."), '
        'then ask "Is there anything you\'d like to change?"'
    )
