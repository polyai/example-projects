from _gen import *  # <AUTO GENERATED>
from functions import idnv, orders, store_info

SMS_KEY = "sms"  # send_link's readback key in orders.asked / same_turn_as_ask


def calling_number_question() -> str:
    """What the caller hears before a text goes to the number they're calling from."""
    return orders.yes_no_question("text the link to the number you're calling from")


def ask_calling_number(conv) -> str:
    orders.asked(conv, SMS_KEY)
    return orders.confirm_instruction(
        calling_number_question(), "send_link", "use_calling_number"
    )


def _ask_number(conv) -> str:
    if idnv.is_valid_phone(idnv.normalize_phone(conv.state.caller_phone)):
        return ask_calling_number(conv)
    return "Ask which mobile number you should text it to. Then call send_link with whatever they say."


@func_description(
    "Text the caller a link, once they've said yes to a text. sms_id is 'tracking_link' for an order's tracking page, or 'website', 'returns_portal', 'store_locator' or 'promotions'."
)
@func_parameter(
    "sms_id",
    "'tracking_link', 'website', 'returns_portal', 'store_locator' or 'promotions'.",
)
def start_send_sms(conv: Conversation, sms_id: str):
    sms_id = (sms_id or "").strip().lower()
    if sms_id == "tracking_link":
        order = orders.selected_order(conv) if idnv.is_verified(conv) else None
        url = orders.tracking_url(order) if order else ""
        if not url:
            return (
                "There's no tracking link for this order yet. Say we'll email one as soon as it "
                "ships, and ask if there's anything else."
            )
        conv.state.sms_body = f"Track your order here: {url}"
    elif sms_id in store_info.LINKS and store_info.sms_body(conv, sms_id):
        conv.state.sms_body = store_info.sms_body(conv, sms_id)
    else:
        conv.log.warning("Unknown sms_id", sms_id=sms_id)
        return "There's no text for that. Give the caller the link in words instead."
    conv.write_metric("SMS_ACCEPTED", sms_id)
    conv.state.sms = {
        "template": "store_link",
        "id": sms_id,
        "pending": "",
        "retries": 0,
    }
    conv.goto_flow("sms_flow")
    return _ask_number(conv)
