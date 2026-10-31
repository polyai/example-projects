from _gen import *  # <AUTO GENERATED>
from functions import idnv

# sms_id -> the variant attribute whose text is sent (config/sms_templates.yaml)
SMS_INFO = {
    "menu": "menu_info",
    "take_out": "take_out_info",
    "private_dining": "private_dining_info",
    "large_party": "group_booking_info",
}


@func_description(
    "Text the caller a link. Only call this when a topic or tool tells you to, with that sms_id, and the caller has said yes to the text."
)
@func_parameter("sms_id", "One of: menu, take_out, private_dining, large_party.")
@func_parameter(
    "phone_number",
    "A number the caller already gave for the text, as they said it. Empty string if none.",
)
def start_send_text(conv: Conversation, sms_id: str, phone_number: str):
    sms_id = (sms_id or "").strip()
    if sms_id not in SMS_INFO:
        conv.log.warning("Unknown sms_id", sms_id=sms_id)
        sms_id = "menu"
    conv.write_metric("SMS_ACCEPTED", sms_id)
    # SMS templates read state variables, not variant attributes.
    conv.state.sms_info = (
        getattr(conv.variant, SMS_INFO[sms_id], "") if conv.variant else ""
    )
    conv.state.sms = {"template": sms_id, "pending": "", "retries": 0, "sent_to": ""}
    conv.state.sms_return_flow = (
        conv.current_flow if conv.current_flow != "sms_flow" else ""
    )
    conv.goto_flow("sms_flow")
    from flows.sms_flow.functions.send_text import ask_calling_number, ask_number

    digits = idnv.normalize_phone(phone_number)
    if idnv.is_valid_phone(digits):
        conv.state.sms = {**conv.state.sms, "pending": digits}
        return ask_number(conv, digits)
    if idnv.is_valid_phone(idnv.normalize_phone(conv.state.caller_phone)):
        return ask_calling_number(conv)
    return "Ask which mobile number you should text the link to. Then call send_text with it."
