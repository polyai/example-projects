from _gen import *  # <AUTO GENERATED>
from functions.modify_booking import modify_booking


@func_description(
    "Add additional booking notes after the booking was already finalized. This function will never be called when modifying bookings."
)
@func_parameter(
    "combined_booking_notes",
    "The booking notes that were mentioned before finalizing the booking and those that were mentioned after finalizing the booking, combined in a single note",
)
def add_notes_after_finalizing_booking(conv: Conversation, combined_booking_notes: str):
    if booking := conv.state.booking:
        date, time = booking["date_time"].split("T")
        return modify_booking(
            conv=conv,
            booking_id=booking.get("reservation_id"),
            new_partysize=booking.get("party_size"),
            new_date=date,
            new_time=time,
            booking_notes=combined_booking_notes,
        )
    return "Immediately call start_confirm_cancel_modify_flow with booking_intent='modify'. After you have identified the booking, you will need to modify the booking with the updated booking notes."
