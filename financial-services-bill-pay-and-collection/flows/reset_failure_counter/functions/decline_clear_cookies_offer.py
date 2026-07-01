from _gen import *  # <AUTO GENERATED>


@func_description("User declined the clear cookies walkthrough offer")
def decline_clear_cookies_offer(conv: Conversation, flow: Flow):
    flow.goto_step("Troubleshooting Login SMS Offer")
    return {
        "utterance": "No problem. You can clear your cookies by going to 'settings', then 'privacy', and selecting 'clear cookies' or 'clear browsing data' for 'all time'. Then you can try logging in again. Would you like me to send you an sms with some help for this instead?"
    }
