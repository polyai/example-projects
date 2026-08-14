from _gen import *  # <AUTO GENERATED>
import re
from datetime import datetime

from functions.customer_core_api import get_email_by_phone
from functions.is_ooh import is_ooh
from functions.oms_connector import get_orders_by_phone_number
from functions.start_function import (
    find_zendesk_user_by_email,
    find_zendesk_user_by_phone,
)
from functions.zendesk_client import create_ticket, init_zendesk_client


@func_description("**Call this function immediately at the start of the call**")
def run_ani_lookup(conv: Conversation, flow: Flow):
    oms_phone_number = re.sub(r"\D+", "", conv.state.phone_number or "")
    if len(oms_phone_number) > 10:
        oms_phone_number = oms_phone_number[-10:]
    conv.state.oms_phone_number = oms_phone_number

    # Customer Core email lookup
    try:
        phone_for_lookup = conv.state.oms_phone_number or conv.state.phone_number
        if not phone_for_lookup:
            conv.log.info("CUSTOMER_CORE: no_phone_provided")
            conv.state.customer_email = None
            conv.state.customer_core_response = None
        else:
            conv.log.info(
                "CUSTOMER_CORE: searching by phone",
                phone_len=len(str(phone_for_lookup)),
            )
            email = get_email_by_phone(conv, phone_for_lookup, timeout=3)
            conv.state.customer_email = email
            conv.log.info(
                "CUSTOMER_CORE: result",
                has_email=bool(email),
                cached_payload=conv.state.customer_core_response is not None,
            )
    except Exception as e:
        conv.log.error("CUSTOMER_CORE call failed", error=str(e))
        conv.state.customer_email = None
        conv.state.customer_core_response = None

    # OMS order lookup
    orders_found = None
    try:
        conv.log.info("OMS: phone search", phone=oms_phone_number)
        orders_found = get_orders_by_phone_number(conv, oms_phone_number, timeout=8)
    except Exception as e:
        conv.log.error("Get orders by phone failed", error=str(e))
        orders_found = None

    if orders_found:
        conv.write_metric("CALLER_PHONE_NUMBER_FOUND")
        conv.state.orders_from_phone_number = orders_found
        if len(orders_found) == 1:
            conv.write_metric("SINGLE_ORDER_FOUND")
        elif len(orders_found) > 1:
            conv.write_metric("MULTIPLE_ORDERS_FOUND")
    else:
        conv.state.verified = False

    # Shipping cache
    conv.state.shipping_order_number_caches = {}

    # Zendesk user lookup
    init_zendesk_client(conv)

    found = False
    rid = conv.memory.get("zd_requester_id")
    if rid:
        conv.state.zendesk_user_id = int(rid)
        conv.log.info("Using requester_id from Agent Memory", requester_id=rid)
        found = True
        conv.write_metric("ZENDESK_USER_FOUND")

    tried_email = False
    tried_phone = False

    if not found:
        if conv.env in ("draft", "sandbox"):
            if conv.state.phone_number:
                tried_phone = True
                found = find_zendesk_user_by_phone(conv)
        else:
            if conv.state.email:
                tried_email = True
                found = find_zendesk_user_by_email(conv)

        if not found:
            if not tried_email and conv.state.email:
                found = find_zendesk_user_by_email(conv)
            if not found and not tried_phone and conv.state.phone_number:
                found = find_zendesk_user_by_phone(conv)

        if found:
            conv.write_metric("ZENDESK_USER_FOUND")

    create_ticket(conv)

    # OOH check
    if is_ooh(conv):
        conv.state.is_ooh = True
    if conv.state.is_ooh:
        conv.write_metric("OOH")

    conv.state.call_start = datetime.now()

    conv.exit_flow()
