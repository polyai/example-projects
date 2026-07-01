from _gen import *  # <AUTO GENERATED>
from functions.utterances import utterance

# from flows.sms_flow.functions.send_sms import send_sms


@func_description("Exit the SMS flow")
def sms_sent_successfully(conv: Conversation, flow: Flow):
    conv.state.sent_sms_to_number = True
    conv.write_metric("SMS_SENT")

    # NARVAR TRACKING LINK STUFF
    if conv.state.item_urls is not None:
        while len(conv.state.item_urls) > 0:
            item = conv.state.item_urls.pop(0)
            conv.state.tracking_sms = item
            conv.send_sms_template(conv.state.sms_phone_number, conv.state.sms_id)

    if conv.state.coming_from_WISMO:
        # conv.say("Great, that's all sent.")
        flow.goto_step("WISMO check")
    else:
        # conv.exit_flow()
        return {
            "utterance": utterance(conv, "sms_sent_anything_else"),
            "transition": {"exit_flow": True},
        }
