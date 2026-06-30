import plog
from _gen import *  # <AUTO GENERATED>
from functions.start_sms_flow import send_sms


@func_description("Use the number from which the user is calling")
def use_phone_number(conv: Conversation, flow: Flow):
    log_prefix = "[use_phone_number]: "
    plog.info(f"{log_prefix} caller_number='{conv.caller_number}'", is_pii=True)
    phone_number = str(conv.caller_number)
    conv.exit_flow()
    return send_sms(conv, phone_number)
