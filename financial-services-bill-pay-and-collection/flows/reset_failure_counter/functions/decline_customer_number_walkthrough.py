from _gen import *  # <AUTO GENERATED>


@func_description("User declined the customer number walkthrough offer")
def decline_customer_number_walkthrough(conv: Conversation, flow: Flow):
    flow.goto_step("Forgot Customer Number SMS Offer")
    return {
        "utterance": "No problem. You can find your 12 digit customer number by going to the login page at www.example-bank.com and clicking 'Forgotten your customer number or username?'. Enter your details and we will send you a text message with your customer number. You can also use your username instead of your customer number. You should clear your cookies or use a different browser before logging in with updated details. Would you like me to send you an sms with some help for this instead?"
    }
