from _gen import *  # <AUTO GENERATED>
from functions import idnv, orders, sms

LINK_IDS = ("tracking_link", "website", "returns_portal", "store_locator", "promotions")


@func_description(
    "Offer to text the caller a link, and send it once they agree. Call it with caller_agreed='false' to get the offer question; call it again with caller_agreed='true' once they've agreed, or straight away if they asked for the text themselves. sms_id is 'tracking_link' for an order's tracking page, or 'website', 'returns_portal', 'store_locator' or 'promotions'."
)
@func_parameter(
    "sms_id",
    "'tracking_link', 'website', 'returns_portal', 'store_locator' or 'promotions'.",
)
@func_parameter(
    "caller_agreed",
    "'true' only if the caller's latest reply agreed to the text offer question you were given ('okay', 'sure' or 'go on' to that question is agreement), or they asked for the text themselves. Otherwise 'false'.",
)
@func_parameter(
    "phone_number",
    "A number the caller gave for the text itself, as they said it; never the number on their account from verification. Empty string if none.",
)
def start_send_sms(
    conv: Conversation, sms_id: str, caller_agreed: str, phone_number: str
):
    sms_id = (sms_id or "").strip().lower()
    if sms_id not in LINK_IDS:
        conv.log.warning("Unknown sms_id", sms_id=sms_id)
        return "There's no text for that. Say the web address in words instead, if there is one."
    offered = sms.offered(conv, sms_id)
    order_number = (offered or {}).get("order_number", "")
    if (
        sms_id == "tracking_link"
        and not order_number
        and not orders.selected_order(conv)
    ):
        # Asked for a tracking link before an order was picked: find the order first.
        if not idnv.is_verified(conv):
            return orders.require(conv, "track_order")
        moving = [
            o
            for o in orders.caller_orders(conv)
            if orders.in_transit(o) and orders.tracking_url(o)
        ]
        if len(moving) == 1:
            order_number = moving[0]["order_number"]
            orders.select(conv, moving[0])
        elif moving:
            return (
                "Call start_track_order with what they said about the order; the tracking offer "
                "comes from there."
            )
    if not sms.link_body(conv, sms_id, order_number):
        if sms_id == "tracking_link":
            return f'Say: "{sms.NO_TRACKING_LINE}" Then ask if there\'s anything else.'
        return "There's no link for that. Say you don't have one to hand."
    conv.write_metric("SMS_OFFERED", sms_id)

    said = idnv.normalize_phone(phone_number)
    if said and said == idnv.state(conv).get("phone"):
        # The number from verification, passed on by the model: not a number given for the
        # text, so the caller is asked for a mobile number (2.8).
        phone_number = ""
    if str(phone_number or "").strip():
        sms.begin(conv, sms_id, order_number)
        conv.goto_flow("sms_flow")
        return sms.take_number(conv, phone_number, "send_link")

    if str(caller_agreed).strip().lower() != "true":
        question = sms.offer(conv, sms_id, order_number)
        return (
            f'Offer the text, in these words: "{question}" {orders.YES_LINE}: call '
            f"start_send_sms with sms_id='{sms_id}' and caller_agreed='true'. If they give another "
            "number, pass it as phone_number."
        )

    conv.write_metric("SMS_ACCEPTED", sms_id)
    calling = sms.calling_number(conv)
    if offered and orders.same_turn_as_ask(conv, sms.SMS_KEY):
        return orders.wait_for_answer(conv, sms.SMS_KEY)
    if offered and offered.get("calling") and calling:
        return sms.send(conv, calling, to_calling=True)
    if calling:
        question = sms.ask_calling_number(conv, sms_id)
        conv.goto_flow("sms_flow")
        return (
            f"Ask: \"{question}\" {orders.YES_LINE}: call send_link with use_calling_number='true'. "
            "If they give another number, call send_link with it."
        )
    sms.begin(conv, sms_id, order_number)
    conv.goto_flow("sms_flow")
    return f'Ask: "{sms.NUMBER_ASK}" Then call send_link with whatever they say.'
