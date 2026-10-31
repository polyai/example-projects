from flows.make_booking.functions.update_booking_request import (
    booking_request,
    next_step,
    offer_or_readback,
    request_state,
    save,
)
from functions.handoff import handoff

from _gen import *  # <AUTO GENERATED>
from functions import bookings, idnv

MAX_UNCLEAR_PHONE = 3


@func_description(
    "Save who the booking is for and how to reach them: the name, the contact number and any note. Call it whenever the caller gives or changes any of these. Once a time has been offered and the name and number are known, it tells you what to read back."
)
@func_parameter(
    "name",
    "The name for the booking as they said it, e.g. 'John Smith'. Empty if not said.",
)
@func_parameter(
    "phone_number",
    "A contact number the caller gave THIS time, as they said it (words or digits). Never add, guess or repeat digits. Empty if none.",
)
@func_parameter(
    "use_calling_number",
    "'true' if the caller said to use the number they're calling from. Otherwise 'false'.",
)
@func_parameter(
    "notes",
    "A note or special request for the restaurant (occasion, allergy, high chair). Empty if none.",
)
def update_booking_details(
    conv: Conversation,
    flow: Flow,
    name: str,
    phone_number: str,
    use_calling_number: str,
    notes: str,
):
    if conv.state.booked_booking_id:
        return (
            "This table is already booked. If the caller wants to change it, call "
            "start_change_booking; for another table, call start_make_booking."
        )

    req = booking_request(conv)
    name, notes = str(name or "").strip(), str(notes or "").strip()
    if name and name.lower() not in ("na", "none", "unknown"):
        req["name"] = " ".join(
            w.capitalize() if w.islower() else w for w in name.split()
        )
    if notes and notes.lower() not in ("na", "none", "no", "nothing"):
        req["notes"] = notes

    calling = idnv.normalize_phone(conv.state.caller_phone)
    if bookings.is_true(use_calling_number) and idnv.is_valid_phone(calling):
        req["phone"], req["phone_from_caller_id"] = calling, True
    elif str(phone_number or "").strip():
        digits = idnv.normalize_phone(phone_number)
        if digits and idnv.is_valid_phone(digits):
            req["phone"], req["phone_from_caller_id"] = digits, False
        elif digits:
            req["phone_unclear"] += 1
            save(conv, req)
            if req["phone_unclear"] >= MAX_UNCLEAR_PHONE:
                return handoff(
                    conv,
                    "BOOKING_PHONE_NOT_CAPTURED",
                    "Sorry, I'm having trouble getting your number. Let me put you through to the "
                    "team to finish the booking, one moment please.",
                )
            return (
                f"NOT A FULL NUMBER (attempt {req['phone_unclear']} of {MAX_UNCLEAR_PHONE}): ask "
                "for the ten-digit number, starting with the area code. Then call "
                "update_booking_details again with whatever they say, even if it's the same as "
                f"before.\n\n{request_state(conv)}"
            )
    save(conv, req)

    if not req.get("offer"):
        return f"Saved. {next_step(conv, req)}\n\n{request_state(conv)}"
    return offer_or_readback(conv, req)
