from _gen import *  # <AUTO GENERATED>


@func_description("This is a function that was created automatically")
def start_confirmation_flow(conv: Conversation):
    conv.goto_flow("IDNV")
    is_cm = getattr(conv.state, "caller_is_case_manager", False)
    if is_cm:
        return {
            "utterance": (
                "I'll need to verify the patient's account. "
                "Is the number you're calling from the one we have on file for the patient?"
            )
        }
    return {
        "utterance": "I'll need to verify your identity so we can look up your account. Is the number you're calling from the one we have on file for you?"
    }
