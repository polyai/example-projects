from _gen import *  # <AUTO GENERATED>


@func_description("User declined the security number reset walkthrough offer")
def decline_security_number_walkthrough(conv: Conversation, flow: Flow):
    flow.goto_step("Reset Security Number SMS Offer")
    return {
        "utterance": "No problem. You can reset your 8 digit security number. When logging in, enter your 12 digit customer number or username and press 'Continue'. Then, click on 'Forgotten your security number?' and follow the steps to reset your details. You should clear your cookies or use a different browser before logging in with your updated details. Would you like me to send you an sms with some help for this instead?"
    }
