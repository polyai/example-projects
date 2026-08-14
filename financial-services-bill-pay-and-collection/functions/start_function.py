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
    upfront_message = upfront_message.strip()

    # import re
    # def tag_sentences(s):  # tag the chunks with [] to prevent the insertion of [friendly] via pronunciation rules
    #     s = '[] ' + s  # tag the start
    #     s = re.sub(r'([.!?…]+\s*)', r'\1[] ', s)  # tag after sentence endings
    #     s = re.sub(r'\[\] $', '', s)  # remove trailing tag
    #     return s.strip()

    if conv.channel_type == "webchat.polyai":
        return {"utterance": "Thanks for contacting Poly Bank. How can I help?"}

    # Out-of-hours: hand off to the Greet User flow, which plays the OOH message
    # and routes urgent callers.
    if conv.state.is_ooh:
        conv.goto_flow("Greet User")
        # Return a short listen timeout so the Greet User flow's initiate_call
        # runs immediately (playing the OOH message) rather than waiting for the
        # caller to speak first, whether or not a disclaimer was spoken upfront.
        return {"utterance": upfront_message or "", "listen": {"asr": {"timeout": 0.1}}}

    # In-hours: greet proactively on the opening turn (in the main voice) so the
    # caller hears a real greeting straight away, instead of the old "Ringtone."
    # placeholder followed by silence until they spoke first.
    conv.functions.set_voice("main")
    greeting = "Hi, thanks for calling Poly Bank — you're speaking with our virtual assistant. How can I help you today?"
    if upfront_message:
        greeting = f"{upfront_message} {greeting}"
    return {"utterance": greeting}
