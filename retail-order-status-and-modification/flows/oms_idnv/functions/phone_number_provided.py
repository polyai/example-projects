from _gen import *  # <AUTO GENERATED>
import re

from flows.oms_idnv.functions.full_order_number_provided import (
    cleanup_full_order_number,
    full_order_number_provided,
    is_valid_full_order_number,
)
from flows.oms_idnv.functions.idnv_utils import (
    ActionsIterator,
    get_bullet_points,
    try_alternative_transcripts,
)
from functions.oms_connector import get_orders_by_phone_number
from functions.step_utils import is_ca_from_orders
from functions.transfer_call import transfer_call
from functions.utterances import utterance


def is_valid_US_number(phone_number: str):
    """
    Validates if a phone_number is a valid US number
    """
    if not phone_number:
        return False
    # Regex pattern to match US numbers
    pattern = r"^(?:\+1|1)?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}$"

    is_match = re.match(pattern, phone_number)
    return is_match


def cleanup_phone_number(number: str):
    number = number.replace("-", "")
    number = number.replace(" ", "")
    number = number.replace(".", "")
    return "".join(char for char in number if char.isdigit())


@func_description(
    "Check the phone number provided is correct. This function must be called every time the user provides a phone number."
)
@func_parameter(
    "phone_number",
    "phone number the user provided (national significant number), eg: 650123456 . If there are dashes, spaces or leading zeros, make sure to remove them. ",
)
def phone_number_provided(conv: Conversation, flow: Flow, phone_number: str):
    conv.state.phone_number = cleanup_phone_number(phone_number)
    conv.log.info("Collected phone number", phone_number=conv.state.phone_number)
    if not is_valid_US_number(conv.state.phone_number):
        # Trying alternative transcripts
        for alternative in try_alternative_transcripts(conv, 10):
            conv.state.phone_number = cleanup_phone_number(alternative)
            if is_valid_US_number(conv.state.phone_number):
                conv.log.info(
                    "Trying alternative phone number",
                    phone_number=conv.state.phone_number,
                )
                break
        else:
            # Check if full order number was provided instead
            for alternative in try_alternative_transcripts(conv, 19):
                if is_valid_full_order_number(cleanup_full_order_number(alternative)):
                    conv.log.info(
                        "Full order number provided instead",
                        order_number=conv.state.full_order_number,
                    )
                    return full_order_number_provided(conv, flow, alternative)

            conv.write_metric("IDNV_PHONE_NUMBER_INVALID")
            conv.state.entered_phone_number_validation = True
            return ActionsIterator(
                "INVALID_PHONE_NUMBER_ACTIONS",
                [
                    {
                        "utterance": utterance(conv, "idnv_phone_invalid"),
                    },
                    {
                        "utterance": utterance(conv, "idnv_phone_try_order"),
                        "content": get_bullet_points(
                            "If the user says they **don't know their order number**, you MUST IMMEDIATELY call the function number_unknown",
                            """If the user says they **can try their order number**, or indicates willingness to provide it (e.g., "yes", "let me get my order number", "I'll try my order number", "how about my order number" etc.), you MUST IMMEDIATELY call order_number_collected.""",
                            'If the user asks to wait (e.g., "Wait", "Wait a while"), immediately call order_number_collected.',
                            'If the user says they want to stick with phone number, say: "Sure. Can I have your phone number again?"',
                            "If the user provides a number again - even if it's the same one, immediately call phone_number_provided.",
                            'If the user requests to speak to someone, immediately call transfer_call with handoff_reason = "IDNV_FAILED"',
                        ),
                    },
                ],
            ).get_next(conv)

    conv.write_metric("IDNV_PHONE_NUMBER_COLLECTED", "True")
    return save_phone_number(conv, flow)


def save_phone_number(conv: Conversation, flow: Flow):
    try:
        orders_found = get_orders_by_phone_number(
            conv, conv.state.phone_number, timeout=10
        )
        conv.state.using_phone_number = True
    except Exception as e:
        conv.log.error("Get orders by phone number API error", e=str(e))
        conv.state.call_summary_additional_context = (
            "The agent attempted to transfer call due to an OMS API error."
        )
        conv.write_metric("API_ERROR", "GET_ORDERS_BY_PHONE")
        return transfer_call(
            conv,
            "DEFAULT",
            "API_ERROR",
            utterance(conv, "idnv_transfer_default"),
        )

    if not orders_found:
        flow.goto_step("Collect phone number")
        return ActionsIterator(
            "ORDERS_NOT_FOUND_ACTION",
            [
                {
                    "utterance": utterance(conv, "idnv_orders_not_found"),
                    "content": get_bullet_points(
                        "If the user provides their phone number-even if it's same number as before-immediately call the function phone_number_provided.",
                        "Otherwise, keep asking for the user's phone number.",
                    ),
                },
                {
                    "utterance": utterance(conv, "idnv_orders_not_found_transfer"),
                    "content": get_bullet_points(
                        "If the user provides their phone number again, immediately call the function phone_number_provided.",
                        "If the user says 'yes', immediately call transfer_call with handoff_reason = 'IDNV_FAILED'",
                        "If the user says 'no' or 'no, thanks', immediately says: 'Can I have your phone number again?'.",
                    ),
                },
            ],
        ).get_next(conv)

    if len(orders_found) == 1 and getattr(
        orders_found[0], "billing_country_code", "US"
    ) not in (
        "US",
        "CA",
    ):
        conv.write_metric("IDNV_INTERNATIONAL_BILLING_ZIP")
        return transfer_call(
            conv,
            "DEFAULT",
            "INTERNATIONAL_BILLING_ZIP",
            utterance(conv, "idnv_international_zip"),
        )

    # Reset Counter before entering next step
    conv.state.use_alternative_number = True
    conv.state.INVALID_PHONE_NUMBER_ACTIONS = None
    conv.state.ORDERS_NOT_FOUND_ACTION = None
    conv.write_metric("IDNV_PHONE_NUMBER_FOUND")
    conv.state.orders_from_phone_number = orders_found

    if len(orders_found) == 1:
        conv.write_metric("SINGLE_ORDER_FOUND")
    elif len(orders_found) > 1:
        conv.write_metric("MULTIPLE_ORDERS_FOUND")

    is_ca = is_ca_from_orders(conv, orders_found)
    postal_label = "postal code" if is_ca else "zipcode"
    step_name = "Collect billing postcode" if is_ca else "Collect billing zipcode"
    if len(orders_found) == 1:
        conv.state.singleton_order = True
        conv.say(
            utterance(conv, "idnv_order_found_single_zip", postal_label=postal_label)
        )
        flow.goto_step(step_name)
    else:
        conv.say(
            utterance(conv, "idnv_order_found_multi_zip", postal_label=postal_label)
        )
        flow.goto_step(step_name)

    # Reset Counter before entering next step
    # conv.state.use_alternative_number = True
    # conv.state.INVALID_PHONE_NUMBER_ACTIONS = None
    # conv.state.ORDERS_NOT_FOUND_ACTION = None
    # conv.write_metric("IDNV_PHONE_NUMBER_FOUND")
    # conv.state.orders_from_phone_number = orders_found
    # flow.goto_step("Collect billing zipcode")
    # conv.say("Great, I can see an order here, I just need to ask a couple security questions. First, what's the billing zipcode associated with the order?")
