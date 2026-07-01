from collections import Counter

from _gen import *  # <AUTO GENERATED>
from functions.transfer_call import transfer_call


def _status_bucket_key(line) -> str:
    cons = getattr(line, "consignments", None) or []
    statuses = [c.shipping_status for c in cons if getattr(c, "shipping_status", None)]
    if not statuses:
        return "FULFILMENT_PROCESSING"
    if any(s in ("CANCELLED", "CANCEL_INITIATED") for s in statuses):
        return "CANCELLED"
    if all(s == "SHIPPED" for s in statuses):
        return "SHIPPED"
    if all(s == "PICKED_BY_CUST" for s in statuses):
        return "PICKED_BY_CUST"
    if all(s == "PICKED" for s in statuses):
        return "PICKED"
    return "FULFILMENT_PROCESSING"


@func_description(
    "Determine what the status of the order is, and so what the next stage of the conversation should be."
)
def determine_order_status(conv: Conversation, flow: Flow):
    conv.write_metric("ORDER_STATUS_FLOW_SUCCESSFUL", write_once=True)
    conv.state.order_status_flow_initiated = True
    conv.state.order_status = conv.state.order_details.order_status
    conv.write_metric("ORDER_STATUS_ID", conv.state.order_status)

    if conv.state.order_details.order_date_time:
        conv.write_metric("ORDER_DATE_TIME", conv.state.order_details.order_date_time)

    conv.state.total_order_lines = len(conv.state.order_details.order_lines)

    if (
        conv.state.picked_order is None
        and len(conv.state.order_details.order_lines) > 1
        and len(
            {
                (consignment.shipping_status, order.fulfilment_type)
                for order in conv.state.order_details.order_lines
                for consignment in order.consignments
            }
        )
        > 1
    ):
        order_items_listing = ""
        for item in conv.state.order_details.order_lines:
            order_items_listing += f"- {item.line_description(conv=conv, include_status=False)}.\n"
        conv.state.order_items_listing = order_items_listing
        flow.goto_step("Decide which item to look at")
        return

    # caller has picked an item, or there's only one item, or all item share the same shipping_status and fullfillment type
    item = conv.state.picked_order or conv.state.order_details.order_lines[0]
    conv.state.item_fulfilment_type = "shipping" if item["fulfilment_type"] == "SHIP" else "pick up"

    auto_scope = getattr(conv.state, "picked_shipment_lines", None)
    if not auto_scope or len(auto_scope) == 1:
        bucket = _status_bucket_key(item)
        if bucket == "SHIPPED":
            all_lines = conv.state.order_details.order_lines
            # group all SHIPPED lines
            auto_scope = [ol for ol in all_lines if _status_bucket_key(ol) == "SHIPPED"]
            # if we actually found multiple shipped lines, use them
            if auto_scope and len(auto_scope) > 1:
                conv.state.picked_shipment_lines = auto_scope

    # scope to the shipment group if one was set by caller selection logic
    items_in_scope = getattr(conv.state, "picked_shipment_lines", None) or [item]
    if len(items_in_scope) > 1:
        conv.log.info(
            "determine_order_status:shipment_group_active",
            group_size=len(items_in_scope),
            order_lines=[ol.order_line_number for ol in items_in_scope],
        )

    scope_consignments = [
        c for it in items_in_scope for c in (getattr(it, "consignments", None) or [])
    ]
    scope_statuses = [
        getattr(c, "shipping_status", None)
        for c in scope_consignments
        if getattr(c, "shipping_status", None)
    ]

    HANDOFF_STATUS_CODE = [
        "700",
        "701",
        "702",
        "703",
        "704",
        "705",
        "706",
        "708",
        "709",
        "710",
        "711",
        "800",
        "801",
        "802",
        "803",
        "900",
    ]
    HANDOFF_STATUS_CODE.extend([str(code) for code in range(804, 821)])

    if item.narvar_shipment_status_code in HANDOFF_STATUS_CODE:
        return transfer_call(
            conv,
            "DEFAULT",
            "HANDOFF_STATUS_CODE",
            "Ah, I've found your order but I think you'll need to speak to someone else about it. One sec while I put you through.",
        )

    if item.narvar_order_number:
        conv.write_metric("NARVAR_TRACKING_NUMBER", item.narvar_order_number)

    if item.narvar_shipment_status_code:
        conv.write_metric("NARVAR_STATUS_CODE", item.narvar_shipment_status_code)

    if item.narvar_shipping_status:
        conv.write_metric("NARVAR_TRACKING_STATUS", item.narvar_shipping_status)

    carrier = next(
        (
            c.carrier_display
            for c in item.consignments
            if hasattr(c, "carrier_display") and c.carrier_display
        ),
        None,
    )
    if carrier:
        conv.write_metric("CARRIER", carrier)

    if item.consignments:
        tracking_urls = {c.tracking_url for c in item.consignments if c.tracking_url}
        is_split_shipment = len(tracking_urls) > 1
        if is_split_shipment:
            conv.write_metric("SPLIT_SHIPMENT")

    if item.expected_delivery_date:
        conv.write_metric("EXPECTED_DELIVERY_DATE", item.expected_delivery_date)

    if len(items_in_scope) == 1:
        conv.state.product_description = (
            f"The item is {item.line_description(conv=conv, include_line_number=False)}"
        )
    else:
        description = "The items are as follows:\n"
        for it in items_in_scope:
            description += f"- {it.line_description(conv=conv, include_line_number=False)}\n"
        conv.state.product_description = description

    # FOR TESTING PROMPTING
    # conv.state.product_description = f"""The items are as follows: Example Socks - Men's (Size L, White/Black) in Accessories category. Quantity: 1. Fulfillment Type: SHIP. Status: SHIPPED. Shipment_Status: Delivered. Delivery_Date: 2025-08-26 12:22:00.Tracking_URL: https://tracking.example-store.com/tracking/ups/?order_number=U7354906850191474688-UVDHCKCP6VFM&tracking_numbers=123456789 - Example Shoes - Men's (Size 10.0, Black/White) in Shoes category. Quantity: 1. Fulfillment Type: SHIP. Status: SHIPPED. Shipment_Status: Delayed. Delivery_Date: 2025-08-29 14:30:00. Tracking_URL: https://tracking.example-store.com/tracking/ups/?order_number=U7354906850191474688-UVDHCKCP6VFM&tracking_numbers=987654321 - Example Shorts - Men's (Size L, Black/Black) in Clothing category. Quantity: 1. Fulfillment Type: SHIP. Status: SHIPPED. Shipment_Status: Delivered. Delivery_Date: 2025-08-28 15:09:00. Tracking_URL: https://tracking.example-store.com/tracking/ups/?order_number=U7354906850191474688-UVDHCKCP6VFM&tracking_numbers=987654321"""

    conv.state.cancelled_NLA_content = f"""
                                    {conv.state.product_description}

                                    Tell the user that unfortunately, you can see that the item(s) has been cancelled. We occasionally find that an item is out of stock while fulfilling an order.

                                    In that case, any pending charge on your card will disappear between 5 to 7 business days, so you won't be charged for the purchase.

                                    {conv.state.instructions_for_descriptions}

                                    Do NOT ask the user questions like: "Is there anything else you'd like to know about this order?". You don't have any additional information to give them!!

                                    *EXAMPLE RESPONSE*
                                    Agent: I can see your order for the Nike Air Max has been cancelled. Unfortunately, we occasionally find that an item is out of stock while fulfilling an order. In that case, any pending charge on your card will disappear between 5 to 7 business days, so you won't be charged for the purchase. Is there anything else I can help you with?

                                    If the user has *already* asked to hear about both/all the items in the order, make sure your response reflects this appropriately.

                                    *EXAMPLE*
                                    Agent: It looks like there are a few items in your order - the Nike Air Max and the Puma Defy Mid. Is there a particular item you'd like to check the status of?
                                    User: Both
                                    Agent: I can see your order for the Nike Air Max has been cancelled. Unfortunately, we occasionally find that an item is out of stock while fulfilling an order. In that case, any pending charge on your card will disappear between 5 to 7 business days, so you won't be charged for the purchase. Now, you mentioned you wanted to hear about both items in the order - shall I check on those Puma Defy Mids for you?

                                    *EXAMPLE*
                                    Agent: It looks like there are a few items in your order - the Nike Air Max and the Puma Defy Mid. Is there a particular item you'd like to check the status of?
                                    User: Both
                                    Agent: I can see your order for the Nike Air Max has been cancelled. Unfortunately, we occasionally find that an item is out of stock while fulfilling an order. In that case, any pending charge on your card will disappear between 5 to 7 business days, so you won't be charged for the purchase. Now, you mentioned you wanted to hear about both items in the order - do you still want me to check the status of the Puma Defy Mids for you?"""

    conv.state.submitted_shipping_content = f"""
                                            If you haven't yet reported an order status to the user, let them know you've pulled up their order details

                                            Tell the user that we will send an email with a tracking link as soon as the item(s) has shipped.

                                            {conv.state.product_description}.

                                            {conv.state.instructions_for_descriptions}


                                            Do NOT ask the user questions like: "Is there anything else you'd like to know about this order?". You don't have any additional information to give them!!

                                            Stick closely to the example response.

                                            *EXAMPLE RESPONSE*
                                            Agent: I can see an order here for some Timberland Euro Hiker shoes in a size 9 that's currently being processed. We'll send an email with a tracking link as soon as it's shipped! Is there anything else I can help you with? """

    conv.state.submitted_pickup_content = f"""Tell the user that we will send an email as soon as it's ready to pick up in store. Also let them know that when they come to pick it up, they'll need to bring their confirmation email and a piece of photo ID, like a driving licence.
                                            {conv.state.product_description}.

                                            {conv.state.instructions_for_descriptions}

                                            Do NOT ask the user questions like: "Is there anything else you'd like to know about this order?". You don't have any additional information to give them!!

                                            Stick closely to the example response.

                                            *EXAMPLE RESPONSE*
                                            Agent: I can see an order here for some Timberland Euro Hiker shoes in a size 9 that's currently being processed. We'll send an email as soon as it's ready to pick up in store! When you come to collect it, just remember to bring the confirmation email and a piece of photo ID, like a driving licence. Is there anything else I can help you with?"""

    conv.state.shipped_content = f"""{conv.state.product_description}

                                    Let the user know the shipment status of each item. If it's relevant, (i.e., it hasn't been delivered yet) tell them the estimated date of delivery. ONLY give them the information that you can have - DO NOT ASSUME anything about where their product is.
                                    For example, if the status is "Just shipped", don't tell the user that they are out for delivery if that's not the case.

                                    If there are multiple products, summarize the statuses in a concise way. Each new item starts with a ' - '. ONLY tell the user information that is included in the shipping status. Offer to send them a tracking link with detailed, up-to-date tracking information for more details.

                                    {conv.state.instructions_for_descriptions}

                                    Let the user know the estimated date of the shipment, but no need to tell them the precise time unless they specifically ask.

                                    **CRITICAL: Handling "Label Created" or "Awaiting Carrier Pickup" Questions**
                                    If the user expresses concern about the tracking showing "label created", "awaiting pickup", "awaiting carrier pickup", "waiting for pickup", "hasn't left the warehouse", or similar early-stage shipping statuses:
                                    - ALWAYS explain confidently: This is a normal part of the shipping process. "Label created" or "awaiting carrier pickup" means the order has been processed and packaged. It's now waiting for [CARRIER] to pick it up for delivery - this is NOT the same as waiting for the customer to pick it up. The carrier will be picking up the parcel soon for the final leg of delivery, and tracking will update as soon as they scan it in.
                                    - Only suggest a transfer if the order has been stuck in this status for 5+ business days
                                    - Example response: "I understand your concern. 'Label created' means your order has been processed and is waiting for FedEx to pick it up from our warehouse - that's different from you picking it up. This is a normal part of shipping. FedEx will scan it in soon and you'll see tracking updates then. The tracking link I'm sending will show the most current information.

                                    Example utterances;
                                    "I can see the Nike Air Max, and Puma shoes are out for delivery and are estimated to be delivered today. The Saucony sneakers are shipping and the estimated delivery date is 08/31.  Do you want me to text you a tracking link for more details? It'll have the most detailed, and up to date information."
                                    "Alright, I see here that the adidas Originals Samba sneakers have shipped and are estimated to be delivered August 30th. The Nike Air Max have been delivered. Do you want me to text you a tracking link for more details? It'll have the most detailed, and up to date information."

                                    *IMPORTANT* It's possible that the user asked about a SPECIFIC item (e.g., Nike shorts) and there are other items in their order. In that case, FIRST give the status of the item they asked about first, THEN briefly summarize the rest of the statuses.
                                    You may want to just give the status of the specific item, but please do that *FIRST* and then summarize the other items listed under "The items are as follows.."
                                    Example utterance;
                                    "The Nike shorts have shipped and should be delivered today. The Nike Air Max, Puma cargo shorts and Adidas sliders have also shipped and are estimated to be delivered by Tuesday. Do you want a tracking link for more details? It'll have the most detailed, and up to date information."

                                    """

    conv.state.shipped_content_no_tracking = f"""{conv.state.product_description}

                                    Let the user know the shipment status of each item. If it's relevant, (i.e., it hasn't been delivered yet) tell them the estimated date of delivery. ONLY give them the information that you can have - DO NOT ASSUME anything about where their product is.
                                    For example, if the status is "Just shipped", don't tell the user that they are out for delivery if that's not the case.

                                    If there are multiple products, summarize the statuses in a concise way. Each new item starts with a ' - '. ONLY tell the user information that is included in the shipping status. Let the user know they can check their email for tracking updates.

                                    {conv.state.instructions_for_descriptions}

                                    Let the user know the estimated date of the shipment, but no need to tell them the precise time unless they specifically ask.

                                    Do NOT offer to send a tracking link or text message — we do not have a tracking link available for this order.

                                    Example utterances;
                                    "I can see the Nike Air Max and Puma shoes are out for delivery and estimated to arrive today. The Saucony sneakers have shipped and the estimated delivery date is 08/31. You should have received a tracking email with more details. Is there anything else I can help with?"
                                    "The adidas Originals Samba sneakers have shipped and are estimated to be delivered August 30th. The Nike Air Max have been delivered. You can check your email for tracking updates. Is there anything else I can help you with?"

                                    *IMPORTANT* It's possible that the user asked about a SPECIFIC item (e.g., Nike shorts) and there are other items in their order. In that case, FIRST give the status of the item they asked about first, THEN briefly summarize the rest of the statuses.

                                    """

    conv.state.pickup_ready_content = f"""Tell the user that the item(s) is ready for in-store pickup. Remind them to bring their confirmation email and a piece of photo ID, like a driving licence.
                                        {conv.state.product_description}

                                        {conv.state.instructions_for_descriptions}

                                        Do NOT ask the user questions like: "Is there anything else you'd like to know about this order?". You don't have any additional information to give them!!

                                        *EXAMPLE RESPONSE*
                                        Agent: The PUMA mid women's in size 5 are ready for pickup! Remember to bring the confirmation email and a piece of photo ID, like a driving licence. Is there anything else I can help you with?"""

    conv.state.pickedup_content = f"""{conv.state.product_description}. Tell the user that you see that the item(s) has been picked up."""

    if conv.state.order_status == "FRAUD_CHECK_FAILED":
        print(">>>>>001")
        conv.state.call_summary_additional_context = "The agent attempted to transfer call because the order has status 'FRAUD_CHECK_FAILED'."
        return transfer_call(
            conv,
            "DEFAULT",
            "FRAUD_CHECK_FAILED",
            "Ah, I've found your order but I think you'll need to speak to someone else about it. One sec while I put you through.",
        )
        # flow.goto_step("Handoff")

    elif conv.state.order_status == "CANCELLED":
        if item.consignments and all(qty.cancel_reason == "NLA" for qty in item.consignments):
            # NLA = item no longer available
            print(">>>>>002")
            return {
                "content": conv.state.cancelled_NLA_content,
                "transition": {
                    "goto_flow": "OMS_WISMO",
                    "goto_step": "Determine what user needs next",
                },
            }
        else:
            # flow.goto_step("Handoff")
            print(">>>>>003")
            conv.state.call_summary_additional_context = "The agent attempted to transfer call because the order has status 'CANCELLED_BY_STORE_NOT_NLA'."
            return transfer_call(
                conv,
                "DEFAULT",
                "CANCELLED_BY_STORE_NOT_NLA",
                "Ah, I've found your order but I think you'll need to speak to someone else about it. One sec while I put you through.",
            )

    elif conv.state.order_status in ["SUBMITTED", "WAIT_FRAUD_SYSTEM_CHECK", "FRAUD_CHECKED"]:
        print(">>>>>004")
        if conv.state.item_fulfilment_type == "shipping":
            return {
                "content": conv.state.submitted_shipping_content,
                "transition": {
                    "goto_flow": "OMS_WISMO",
                    "goto_step": "Determine what user needs next",
                },
            }

        elif conv.state.item_fulfilment_type == "pick up":
            return {
                "content": conv.state.submitted_pickup_content,
                "transition": {
                    "goto_flow": "OMS_WISMO",
                    "goto_step": "Determine what user needs next",
                },
            }

    elif conv.state.order_status == "FULFILMENT_PROCESSING":
        # Use scope_consignments/scope_statuses (derived earlier) instead of item.consignments
        cancelled_item = next(
            (
                c
                for c in scope_consignments
                if c.shipping_status in ["CANCEL_INITIATED", "CANCELLED"]
            ),
            None,
        )
        if cancelled_item:
            if getattr(cancelled_item, "cancel_reason", None) == "NLA":
                print(">>>>>1")
                return {
                    "content": conv.state.cancelled_NLA_content,
                    "transition": {
                        "goto_flow": "OMS_WISMO",
                        "goto_step": "Determine what user needs next",
                    },
                }
            else:
                # flow.goto_step("Handoff")
                print(">>>>>2")
                conv.state.call_summary_additional_context = "The agent attempted to transfer call because the order has status 'CANCELLED_BY_STORE_NOT_NLA'."
                return transfer_call(
                    conv,
                    "DEFAULT",
                    "CANCELLED_BY_STORE_NOT_NLA",
                    "Ah, I see your order but I think you'll need to speak to someone else about it. One sec while I put you through.",
                )

        elif scope_consignments and all(s in ["CREATED", "SUBMITTED"] for s in scope_statuses):
            print(">>>>>3")
            if conv.state.item_fulfilment_type == "shipping":
                return {
                    "content": conv.state.submitted_shipping_content,
                    "transition": {
                        "goto_flow": "OMS_WISMO",
                        "goto_step": "Determine what user needs next",
                    },
                }

            elif conv.state.item_fulfilment_type == "pick up":
                return {
                    "content": conv.state.submitted_pickup_content,
                    "transition": {
                        "goto_flow": "OMS_WISMO",
                        "goto_step": "Determine what user needs next",
                    },
                }

        elif scope_consignments and all(s == "SHIPPED" for s in scope_statuses):
            print(">>>>>4")
            # Aggregate ALL tracking links for the current scope
            urls = {c.tracking_url for c in scope_consignments if getattr(c, "tracking_url", None)}
            conv.state.tracking_urls = list(urls)
            conv.state.tracking_url = next(iter(urls), "")  # legacy single link
            return {
                "content": conv.state.shipped_content
                if urls
                else conv.state.shipped_content_no_tracking,
                "transition": {
                    "goto_flow": "OMS_WISMO",
                    "goto_step": "Offer NARVAR tracking link"
                    if urls
                    else "Determine what user needs next",
                },
            }

        elif scope_consignments and all(s == "PICKED" for s in scope_statuses):
            print(">>>>>5")
            return {
                "content": conv.state.pickup_ready_content,
                "transition": {
                    "goto_flow": "OMS_WISMO",
                    "goto_step": "Determine what user needs next",
                },
            }

        else:
            # Mixed/unclear within scope -> disambiguate entries
            print(">>>>>6")
            setup_order_entries_disambiguation_step(conv, item)
            flow.goto_step("Decide which item entry to look at")

    elif conv.state.order_status == "FULFILMENT_COMPLETE":
        # Compute statuses from the scope
        shipping_statuses = set(scope_statuses)

        if shipping_statuses == {"PICKED_BY_CUST"}:
            print(">>>>>A")
            return {
                "content": conv.state.pickedup_content,
                "transition": {
                    "goto_flow": "OMS_WISMO",
                    "goto_step": "Determine what user needs next",
                },
            }

        elif shipping_statuses.issubset(["CANCELLED", "PICKED_BY_CUST"]):
            if all(
                getattr(c, "cancel_reason", None) in ["NLA", None]
                for c in scope_consignments
                if c.shipping_status in ["CANCELLED", "CANCEL_INITIATED"]
            ):
                print(">>>>>B")
                return {
                    "content": conv.state.cancelled_NLA_content,
                    "transition": {
                        "goto_flow": "OMS_WISMO",
                        "goto_step": "Determine what user needs next",
                    },
                }
            else:
                # flow.goto_step("Handoff")
                print(">>>>>C")
                conv.state.call_summary_additional_context = "The agent attempted to transfer call because the order has status 'CANCELLED_BY_STORE_NOT_NLA'."
                return transfer_call(
                    conv,
                    "DEFAULT",
                    "CANCELLED_BY_STORE_NOT_NLA",
                    "Ah, I see your order but I think you'll need to speak to someone else about it. One sec while I put you through.",
                )

        elif scope_consignments and shipping_statuses.issubset(["SHIPPED"]):
            print(">>>>>D")
            # Aggregate ALL tracking links for the current scope
            urls = {c.tracking_url for c in scope_consignments if getattr(c, "tracking_url", None)}
            conv.state.tracking_urls = list(urls)
            conv.state.tracking_url = next(iter(urls), "")
            return {
                "content": conv.state.shipped_content
                if urls
                else conv.state.shipped_content_no_tracking,
                "transition": {
                    "goto_flow": "OMS_WISMO",
                    "goto_step": "Offer NARVAR tracking link"
                    if urls
                    else "Determine what user needs next",
                },
            }

        elif shipping_statuses.issubset(["PICKED_BY_CUST"]):
            print(">>>>>E")
            # Representative link from scope if present (usually empty here)
            conv.state.tracking_url = next(
                (c.tracking_url for c in scope_consignments if getattr(c, "tracking_url", None)), ""
            )
            return {
                "content": conv.state.pickedup_content,
                "transition": {
                    "goto_flow": "OMS_WISMO",
                    "goto_step": "Determine what user needs next",
                },
            }

        else:
            print(">>>>>F")
            # Mixed statuses within scope -> disambiguate entries
            setup_order_entries_disambiguation_step(conv, item)
            flow.goto_step("Decide which item entry to look at")


def setup_order_entries_disambiguation_step(conv: Conversation, item):
    conv.state.item_description = (
        f"{item.product_brand} {item.product_name} "
        f"(Size {item.product_size}, {item.product_color}) in "
        f"{item.product_category} category. "
        f"Fulfillment Type: {item.fulfilment_type}. "
    )

    status_counter = Counter(f"{consignment.shipping_status}" for consignment in item.consignments)

    item_entries_description = ""
    for status, count in status_counter.items():
        item_entries_description += f"- Status: {status}; Quantity: {count}\n"
    conv.state.item_entries_description = item_entries_description
    conv.state.item_to_look_at = item
