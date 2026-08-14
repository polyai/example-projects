from _gen import *  # <AUTO GENERATED>


@func_description(
    "Called when the user confirms the phone number read back to them is correct."
)
def phone_confirmed(conv: Conversation, flow: Flow):
    conv.write_metric("IDNV_PHONE_CONFIRMED", True)
    flow.goto_step("save_collected_phone_and_lookup")
    return {}
