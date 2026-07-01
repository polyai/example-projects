from _gen import *  # <AUTO GENERATED>


@func_description("Route based on which login details the user is missing")
@func_parameter(
    "missing_detail",
    'Which detail the user is missing. Choose from: "has_all_details", "unsure", "customer_number", "password", "security_number".',
)
def route_missing_details(conv: Conversation, flow: Flow, missing_detail: str):
    missing_detail = missing_detail.lower().strip()

    if missing_detail == "has_all_details":
        flow.goto_step("Has All Details")
        return {
            "utterance": "Okay, if you know all your details I'd recommend clearing your cookies or using a different browser. If you've already tried this, then the best thing to do would be to reset your password to unlock your account. Would you like me to walk you through how to clear your cookies now?"
        }

    if missing_detail == "unsure":
        flow.goto_step("Explain Missing Details")
        return {
            "utterance": "You can unlock your account with either your 8 Digit Security Number or your Password, plus your 12 Digit Customer Number or your Username, and your registered phone number. Do you have access to all of these?"
        }

    if missing_detail == "customer_number":
        flow.goto_step("Customer Number Walkthrough")
        return {
            "utterance": "Ok, so you can get your 12 digit customer number on our website at www.example-bank.com when logging in. Would you like me to walk you through how to do that now?"
        }

    if missing_detail == "password":
        flow.goto_step("Password Walkthrough")
        return {
            "utterance": "Ok, so you can reset your password when logging in. Would you like me to walk you through how to do that now?"
        }

    if missing_detail == "security_number":
        flow.goto_step("Security Number Walkthrough")
        return {
            "utterance": "Ok, so you can reset your 8 digit security number when logging in. Would you like me to walk you through how to do that now?"
        }

    conv.log.warning("Unexpected missing_detail value", missing_detail=missing_detail)
    flow.goto_step("Collect Missing Details")
    return "Ask the user again which details they are missing for Online Banking."
