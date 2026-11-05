import functions.new_booking as nb
from _gen import *  # <AUTO GENERATED>
from functions import bookings


@func_description(
    "Save who the booking is for and how to reach them: the name, the contact number and any note. Call it whenever the caller gives or changes any of these, or answers the question about the number they're calling from or the note question."
)
@func_parameter(
    "name",
    "The name for the booking as they said it, e.g. 'Tom Baker'. Empty if not said.",
)
@func_parameter(
    "phone_number",
    "A contact number the caller gave THIS time, as they said it (words or digits). Never add, guess or repeat digits. Empty if none.",
)
@func_parameter(
    "use_calling_number",
    "'true' if the caller said yes, or an acknowledgement ('okay', 'yeah'), to the question whether the number they're calling from is the best one. 'false' if they said no to it. Empty otherwise.",
)
@func_parameter(
    "notes",
    "Anything the restaurant should know (an allergy, an occasion, a table request), in a few of the caller's words. 'none' only if the caller themselves said there's nothing (in answer to the note question, or on their own). Empty if they haven't said anything about it.",
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

    req = nb.booking_request(conv)
    name, notes = str(name or "").strip(), str(notes or "").strip()
    if name and name.lower() not in ("na", "none", "unknown"):
        req["name"] = " ".join(
            w.capitalize() if w.islower() else w for w in name.split()
        )
    if notes:
        if notes.lower().strip(" .!") not in nb.NO_NOTE:
            req["notes"], req["notes_answered"] = notes, True
        else:
            req["notes_answered"] = True  # "no" is an answer

    calling = nb.caller_id(conv)
    answer = str(use_calling_number or "").strip().lower()
    if answer == "true" and calling and not str(phone_number or "").strip():
        if bookings.asked_this_turn(conv, nb.CALLER_ID_KEY):
            nb.save(conv, req)
            return {"utterance": nb.CALLER_ID_QUESTION}
        req["phone"], req["phone_from_caller_id"] = calling, True
    elif (
        answer == "false"
        and calling
        and not req["phone"]
        and not str(phone_number or "").strip()
    ):
        req["caller_id_declined"] = True
    elif str(phone_number or "").strip():
        retry = nb.take_phone(conv, req, phone_number, "update_booking_details")
        if retry is not None:
            return retry
    nb.save(conv, req)

    if not req.get("offer"):
        return f"Saved. {nb.next_step(conv, req)}\n\n{nb.request_state(conv, req)}"
    return nb.after_details(conv, req)
