import requests
from _gen import *  # <AUTO GENERATED>
from flows.oms_idnv.functions.idnv_utils import (
    ActionsIterator,
    get_bullet_points,
    try_alternative_transcripts,
)
from flows.oms_idnv.functions.normalize_order_number import try_normalize_order_number
from functions.oms_connector import get_order_details
from functions.step_utils import is_ca_from_order
from functions.transfer_call import transfer_call
from functions.utterances import utterance


def cleanup_full_order_number(number: str) -> str:
    number = number.replace("-", "")
    number = number.replace(" ", "")
    number = number.replace(".", "")
    digits = "".join(char for char in number if char.isdigit())
    # Preserve the letter prefix (P, U, T, etc.) if present
    first_alpha = next((c for c in number if c.isalpha()), None)
    if first_alpha:
        return first_alpha.upper() + digits
    return digits


def is_valid_full_order_number(order_number: str) -> bool:
    # 20 chars = letter prefix + 19 digits (e.g. P7445152414656626688)
    # 19 chars = digits only via DTMF (user can't type the letter prefix)
    return len(order_number) in (19, 20)


@func_description("Check that the order number that the user just provided is correct.")
@func_parameter(
    "full_order_number",
    "The full order number user provided. May start with 'P', a zero, or a one.",
)
def full_order_number_provided(conv: Conversation, flow: Flow, full_order_number: str):
    conv.state.using_phone_number = False
    conv.state.full_order_number = cleanup_full_order_number(full_order_number)
    conv.log.info("Collected full order number", order_number=conv.state.full_order_number)
    conv.write_metric("ORDER_NUMBER_COLLECTED")

    if not is_valid_full_order_number(conv.state.full_order_number):
        conv.log.info(
            "Invalid order number, trying alternatives",
            invalid_order_number=conv.state.full_order_number,
        )

        # Try LLM-based normalization (handles French spoken digits)
        llm_normalized = try_normalize_order_number(conv, full_order_number)
        if llm_normalized and is_valid_full_order_number(llm_normalized):
            conv.state.full_order_number = llm_normalized
            conv.log.info(
                "LLM-normalized order number",
                order_number=conv.state.full_order_number,
            )
        else:
            # Trying alternative transcripts
            for alternative in try_alternative_transcripts(conv, 19):
                conv.state.full_order_number = cleanup_full_order_number(alternative)
                if is_valid_full_order_number(conv.state.full_order_number):
                    conv.log.info(
                        "Trying alternative full order number",
                        order_number=conv.state.full_order_number,
                    )
                    break
            else:
                return ActionsIterator(
                    "INVALID_FULL_ORDER_NUMBER_ACTIONS",
                    [
                        {
                            "utterance": utterance(conv, "idnv_order_invalid"),
                            "content": get_bullet_points(
                                "If the user provides a number again—even if it's the same one—"
                                "immediately call full_order_number_provided."
                            ),
                        },
                        {
                            "utterance": utterance(conv, "idnv_order_not_found_transfer"),
                            "content": get_bullet_points(
                                "If the user says 'yes', immediately call transfer_call with "
                                "handoff_reason = 'IDNV_FAILED'",
                                "If the user says 'no' or 'no, thanks', immediately says: "
                                "'Can I have your order number again?'.",
                            ),
                        },
                    ],
                ).get_next(conv)

    conv.log.info(
        "Confirming order number with caller",
        order_number=conv.state.full_order_number,
    )

    return save_full_order_number(conv, flow)


def _try_lookup_order(conv, order_number: str):
    """Try to look up an order, retrying with alternate prefixes if the first lookup fails.

    Prod orders use P or U prefix, test orders use T. ASR may mishear the letter,
    and DTMF input won't have one at all. We try the original, then common prefixes.
    """
    order_found = get_order_details(conv, order_number, timeout=10)
    if order_found:
        return order_found

    digits = "".join(c for c in order_number if c.isdigit())
    original_prefix = order_number[0:1].upper() if order_number[0:1].isalpha() else ""

    # Try alternate prefixes (P or U for prod, T for test)
    for prefix in ("P", "U", "T"):
        if prefix == original_prefix:
            continue
        alt = prefix + digits
        conv.log.info("Order not found, retrying with prefix", original=order_number, alt=alt)
        order_found = get_order_details(conv, alt, timeout=10)
        if order_found:
            conv.state.full_order_number = alt
            return order_found

    # Also try digits-only (no prefix) if we haven't already
    if original_prefix and len(digits) == 19:
        order_found = get_order_details(conv, digits, timeout=10)
        if order_found:
            conv.state.full_order_number = digits
    return order_found


def save_full_order_number(conv: Conversation, flow: Flow):
    try:
        order_found = _try_lookup_order(conv, conv.state.full_order_number)
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            order_found = None
        else:
            conv.log.error("Get orders by order number API error: %s", str(e))
            conv.write_metric("API_ERROR", "GET_ORDERS_BY_ORDER_NUM")
            return transfer_call(
                conv,
                "DEFAULT",
                "API_ERROR",
                utterance(conv, "idnv_transfer_default"),
            )
    except Exception as e:
        conv.log.error("Get orders by order number API error", e=str(e))
        conv.state.call_summary_additional_context = (
            "The agent attempted to transfer call due to an OMS API error."
        )
        conv.write_metric("API_ERROR", "GET_ORDERS_BY_ORDER_NUM")
        return transfer_call(
            conv,
            "DEFAULT",
            "API_ERROR",
            utterance(conv, "idnv_transfer_default"),
        )

    if not order_found:
        flow.goto_step("Collect full order number")
        conv.write_metric("ORDER_NOT_FOUND")
        return ActionsIterator(
            "ORDERS_NOT_FOUND_ACTION_2",
            [
                {
                    "utterance": utterance(conv, "idnv_order_not_found"),
                },
                {
                    "utterance": utterance(conv, "idnv_order_not_found_transfer"),
                    "content": get_bullet_points(
                        "If the user provides their order number again, immediately call the function order_number_provided.",
                        "If the user says 'yes', immediately call transfer_call with handoff_reason = 'IDNV_FAILED'",
                        "If the user says 'no' or 'no, thanks', immediately says: 'Can I have your order number again?'.",
                    ),
                },
            ],
        ).get_next(conv)
    if getattr(order_found, "billing_country_code", "US") not in ("US", "CA"):
        conv.write_metric("IDNV_INTERNATIONAL_BILLING_ZIP")
        return transfer_call(
            conv,
            "DEFAULT",
            "INTERNATIONAL_BILLING_ZIP",
            utterance(conv, "idnv_international_zip"),
        )

    conv.write_metric("ORDER_NUMBER_MATCHED")
    conv.state.INVALID_FULL_ORDER_NUMBER_ACTIONS = None
    conv.state.ORDERS_NOT_FOUND_ACTION_2 = None
    conv.write_metric("ORDER_FOUND")
    conv.write_metric("ORDER_NUMBER", conv.state.full_order_number)
    conv.write_metric("ORDER_STATUS", order_found.order_status)
    conv.state.order_from_full_order_number = order_found
    is_ca = is_ca_from_order(conv, order_found)
    postal_label = "postal code" if is_ca else "zipcode"
    step_name = "Collect billing postcode" if is_ca else "Collect billing zipcode"
    conv.say(utterance(conv, "idnv_order_confirm_zip", postal_label=postal_label))
    flow.goto_step(step_name)
