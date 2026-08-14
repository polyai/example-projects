import plog

from _gen import *  # <AUTO GENERATED>
from functions.start_sms_flow import send_sms


@func_description(
    "Call this function if you read the phone number back to the user and the user confirmed it"
)
def phone_number_confirmed(conv: Conversation, flow: Flow):
    log_prefix = "[phone_number_confirmed]: "
    plog.info(
        f"{log_prefix} phone_number_given_in_history='{conv.state.phone_number_given_in_history}', "
        f"sms_phone_number='{getattr(conv.state, 'sms_phone_number', None)}'",
        is_pii=True,
    )
    if not conv.state.phone_number_given_in_history:
        return "You need to first save the phone number by calling the phone_number_given function."

    conv.exit_flow()
    return send_sms(conv, conv.state.sms_phone_number)
