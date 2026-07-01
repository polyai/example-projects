from _gen import *  # <AUTO GENERATED>
from functions.handoff_utils import is_vulnerable_customer
from functions.time_utils import is_ooh, set_datetime


def start_function(conv: Conversation):
    conv.log.info(
        "Integration attributes",
        sip_headers=conv.sip_headers,
        integration_attributes=conv.integration_attributes,
    )

    set_datetime(conv)
    conv.state.is_ooh = is_ooh(conv)
    if conv.state.is_ooh:
        conv.write_metric("OOH_CALL", write_once=True)

    # agent memory
    # write_repeat_caller_metrics(conv)

    # check if customer is vulnerable
    conv.state.is_vulnerable_customer = is_vulnerable_customer(conv)
    if conv.state.is_vulnerable_customer:
        conv.write_metric("VULNERABLE_CUSTOMER", write_once=True)

    # if conv.caller_number == 'nicole.soh@poly-ai.com':
    #     conv.state.is_vulnerable_customer = True
    #     conv.write_metric("VULNERABLE_CUSTOMER", write_once=True)
    # read VC keywords into state
    conv.functions.vc_keywords()

    # disclaimer and emergency message

    conv.functions.set_voice("disclaimer")

    upfront_messaging = conv.real_time_config.get("upfront_messaging", {})
    disclaimer = upfront_messaging.get("disclaimer", "")
    disclaimer_active = upfront_messaging.get("disclaimer_active", False)
    emergency_message = upfront_messaging.get("emergency_message", "")
    emergency_active = upfront_messaging.get("disclaimer_active", False)

    upfront_message = ""

    if disclaimer_active:
        upfront_message += disclaimer
    if emergency_active:
        upfront_message += " " + emergency_message
    if upfront_message and not upfront_message.endswith("."):
        upfront_message += "."
    upfront_message += " Ringtone."
    upfront_message = upfront_message.strip()

    # import re
    # def tag_sentences(s):  # tag the chunks with [] to prevent the insertion of [friendly] via pronunciation rules
    #     s = '[] ' + s  # tag the start
    #     s = re.sub(r'([.!?…]+\s*)', r'\1[] ', s)  # tag after sentence endings
    #     s = re.sub(r'\[\] $', '', s)  # remove trailing tag
    #     return s.strip()

    if conv.channel_type == "webchat.polyai":
        return {"utterance": "Thanks for contacting Poly Bank. How can I help?"}
    conv.goto_flow("Greet User")
    return {
        "utterance": upfront_message
        # "utterance": tag_sentences(upfront_message)
    }
