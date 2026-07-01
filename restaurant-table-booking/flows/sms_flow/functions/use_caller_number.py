from _gen import *  # <AUTO GENERATED>
from functions.send_sms import send_sms


@func_description(
    "Function for if the user states we can send an sms to the number they are calling from"
)
@func_latency_control(
    delay_before_responses_start=7,
    silence_after_each_response=0,
    delay_responses=[("One moment while I send that...", 3)],
)
def use_caller_number(conv: Conversation, flow: Flow):
    conv.state.sms_phone_number = conv.caller_number
    flow.goto_step("send_sms")
    return send_sms(conv, conv.caller_number)
