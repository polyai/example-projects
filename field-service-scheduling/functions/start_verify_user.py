from _gen import *  # <AUTO GENERATED>


@func_description("Enter the verify_user flow")
def start_verify_user(conv: Conversation):
    conv.write_metric("CUSTOMER_VERIFICATION_INITIATED", None)
    if conv.state.customer_details_list:
        conv.log.info("Number exists")
        return {
            "content": "Before doing anything else, verify if the user is calling from the number associated with their account.",
            "transition": {
                "goto_flow": "verify_user",
                "goto_step": "Should collect phone number",
            },
        }
    else:
        conv.log.info("Ask for number")
        return {
            "content": "Before doing anything else, you will need to look up the user using the phone number associated with their account.",
            "transition": {
                "goto_flow": "verify_user",
                "goto_step": "Collect associated phone number",
            },
        }
