from _gen import *  # <AUTO GENERATED>
from functions.send_sms import send_sms


@func_description("Transition to step save alternative number")
@func_parameter("sms_phone_number", "The phone number the user has provided")
@func_latency_control(
    delay_before_responses_start=5,
    silence_after_each_response=0,
    delay_responses=[("One moment while I send that...", 3)],
)
def save_alternative_number(conv: Conversation, flow: Flow, sms_phone_number: str):
    sms_phone_number = (
        sms_phone_number.replace("-", "")
        .replace(" ", "")
        .replace("(", "")
        .replace(")", "")
        .replace(".", "")
    )
    conv.state.sms_phone_number = sms_phone_number
    conv.state.readback_occurred = True
    flow.goto_step("send_sms")
    return send_sms(conv, sms_phone_number)
