from _gen import *  # <AUTO GENERATED>


@func_description(
    "Called when the caller confirms they are an existing patient at Poly Clinic. Advances to the work injury / auto accident check."
)
def caller_is_existing_patient(conv: Conversation, flow: Flow) -> dict:
    conv.write_metric("BOOKING_EXISTING_PATIENT_CONFIRMED")
    flow.goto_step("Check Work Injury")
    return {
        "content": (
            "Ask the caller if this appointment is related to a work injury or auto accident."
        )
    }
