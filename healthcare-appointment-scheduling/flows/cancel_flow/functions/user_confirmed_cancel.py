from _gen import *  # <AUTO GENERATED>


@func_description(
    "Transition to collect the cancellation reason after the user confirms they want to cancel."
)
def user_confirmed_cancel(conv: Conversation, flow: Flow):
    """Move to the step that collects the user's cancellation reason."""
    flow.goto_step("Collect Cancel Reason")
    is_cm = getattr(conv.state, "caller_is_case_manager", False)
    if is_cm:
        return {
            "utterance": "In order to process this cancellation, could you tell me the patient's reason for cancelling the appointment today?"
        }
    return {
        "utterance": "In order to process this cancellation, could you tell me the reason for cancelling your appointment today?"
    }
