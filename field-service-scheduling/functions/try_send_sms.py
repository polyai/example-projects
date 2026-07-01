from _gen import *  # <AUTO GENERATED>
from functions.handoff import handoff


@func_description("try send sms")
def try_send_sms(conv: Conversation):
    sms_phone_number = "+" + conv.state.sms_country_code + conv.state.sms_phone_number
    try:
        conv.log.info(
            f"sending SMS {conv.state.sms_template_id} to phone number {sms_phone_number}",
            sms_template_id=conv.state.sms_template_id,
            sms_phone_number=sms_phone_number,
        )
        conv.send_sms_template(sms_phone_number, conv.state.sms_template_id)
        conv.write_metric("SMS_SENT", None, write_once=False)
        conv.write_metric("SMS_ID", conv.state.sms_template_id, write_once=False)
    except Exception:
        conv.write_metric("SMS_FAILED", None, write_once=False)
        conv.log.error("SMS failed to send.", exc_info=True)
        return handoff(
            conv,
            "CANNOT_SEND_SMS",
            "I'm sorry, that didn't seem to work. Let me put you through to a team member, one moment please!",
            "CUSTOMER_CARE",
        )

    conv.state.already_sent_to_number = True
    conv.log.info("SMS successfully sent.")
    if conv.current_flow == "sms_flow":
        conv.exit_flow()
    return """Let the user know that the SMS has been sent. Do not read the number back to them again.
    """
