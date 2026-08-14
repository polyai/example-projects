from _gen import *  # <AUTO GENERATED>


@func_description(
    "Called when the user confirms the date of birth read back to them is correct."
)
def dob_confirmed(conv: Conversation, flow: Flow):
    conv.write_metric("IDNV_DOB_CONFIRMED_BY_CALLER", True)
    flow.goto_step("match_dob_and_identify")
    return {}
