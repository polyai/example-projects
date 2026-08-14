from _gen import *  # <AUTO GENERATED>


@func_description(
    "Called when the caller confirms they are an existing patient. Advances to appointment type collection."
)
def caller_is_existing_patient(conv: Conversation, flow: Flow) -> dict:
    conv.write_metric("BOOKING_EXISTING_PATIENT_CONFIRMED", True)
    flow.goto_step("Collect Appointment Type")
    return {
        "content": "Ask the caller what type of appointment they would like to book."
    }
