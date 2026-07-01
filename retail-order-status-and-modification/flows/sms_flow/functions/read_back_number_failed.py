from _gen import *  # <AUTO GENERATED>
from functions.utterances import utterance


@func_description(
    "The user said the number was incorrect after reading it back. Try and collect phone number one more time."
)
@func_parameter(
    "readback_failed_once",
    "Flags whether we've already failed once reading back the number. Defaults to FALSE.",
)
def read_back_number_failed(conv: Conversation, flow: Flow, readback_failed_once: bool):
    if conv.state.readback_failed_once:
        conv.write_metric("SMS_FAILED")
        failed_step = (
            "WISMO check - sending failed" if conv.state.coming_from_WISMO else "SMS failed"
        )
        return {
            "utterance": utterance(conv, "sms_failed_text"),
            "transition": {"goto_flow": "SMS flow", "goto_step": failed_step},
        }
    else:
        conv.state.readback_failed_once = True
        flow.goto_step("Phone number collected")
