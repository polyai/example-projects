import plog
from _gen import *  # <AUTO GENERATED>


@func_description("Save the cell phone number provided by the caller during booking.")
@func_parameter(
    "phone_number", "The 10-digit cell phone number provided by the caller (no country code)."
)
def cell_phone_given(conv: Conversation, flow: Flow, phone_number: int):
    log_prefix = "[cell_phone_given]: "
    plog.info(f"{log_prefix} phone_number='{phone_number}'", is_pii=True)

    MIN_DIGITS = 10
    MAX_DIGITS = 10

    if len(str(phone_number)) < MIN_DIGITS:
        return {
            "utterance": "Sorry, I didn't quite catch the full number. Could you try again, or type it in on the keypad?"
        }
    if len(str(phone_number)) > MAX_DIGITS:
        return {"utterance": "Just to be sure, could you type that number in on your keypad?"}

    conv.state.booking_cell_phone = str(phone_number)

    return {"utterance": f"Thanks. Just to confirm, that was {phone_number}?"}
