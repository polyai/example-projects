from _gen import *  # <AUTO GENERATED>
from functions.util_functions import is_valid_uk_mobile_number


@func_description("Transition to step check_user_number")
def go_to_check_user_number(conv: Conversation, flow: Flow):
    conv.state.readback_occurred = False

    if conv.state.already_sent_to_number:
        flow.goto_step("send_sms")
        return "You already collected a number once, no need to collect it again."
    elif is_valid_uk_mobile_number(conv.state.phone_number):
        flow.goto_step("Ask this number")
    else:
        flow.goto_step("Collect phone number")
