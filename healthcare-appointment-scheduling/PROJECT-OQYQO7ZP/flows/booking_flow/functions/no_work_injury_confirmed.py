from _gen import *  # <AUTO GENERATED>


@func_description(
    "Called when the caller confirms this appointment is not related to a work injury or auto accident. Advances to the appointment category collection step."
)
def no_work_injury_confirmed(conv: Conversation, flow: Flow) -> dict:
    flow.goto_step("Collect Appointment Category")
    if conv.state.caller_is_case_manager:
        return {"content": "Ask the case manager what type of appointment the patient needs."}
    return {"content": "Ask the caller what type of appointment they'd like to book."}
