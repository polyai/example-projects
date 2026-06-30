from _gen import *  # <AUTO GENERATED>


@func_description("Called when the user provides a phone number for account lookup.")
@func_parameter("phone_number", "The phone number the user provided.")
def phone_number_collected(conv: Conversation, flow: Flow, phone_number: str):
    digits = "".join(c for c in phone_number if c.isdigit())
    conv.state.idnv_collected_phone = digits
    flow.goto_step("Confirm Phone Number")
    return {}
