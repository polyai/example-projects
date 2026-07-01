from _gen import *  # <AUTO GENERATED>


@func_description("User declined the password reset walkthrough offer")
def decline_password_walkthrough(conv: Conversation, flow: Flow):
    flow.goto_step("Reset Password SMS Offer")
    return {
        "utterance": "No problem. When logging in, enter your 12 digit customer number or username and press 'Continue'. Then click 'Forgotten your password?' and follow the steps to reset your details. You should clear your cookies or use a different browser before logging in with updated details. Would you like me to send you an sms with some help for this instead?"
    }
