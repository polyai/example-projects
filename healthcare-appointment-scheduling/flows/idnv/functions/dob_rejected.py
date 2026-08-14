from _gen import *  # <AUTO GENERATED>


@func_description(
    "Called when the user says the date of birth read back to them is wrong."
)
def dob_rejected(conv: Conversation, flow: Flow):
    flow.goto_step("Collect Date of Birth")
    return {"content": "Ask the user to provide their date of birth again."}
