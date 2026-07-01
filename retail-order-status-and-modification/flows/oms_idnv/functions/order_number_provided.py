from _gen import *  # <AUTO GENERATED>
from flows.oms_idnv.functions.idnv_utils import (
    ActionsIterator,
    get_bullet_points,
    try_alternative_transcripts,
)
from flows.oms_wismo.functions.determine_order_status import determine_order_status
from functions.utterances import utterance


def is_valid_last_4_digits(digits: str):
    return len(digits) == 4


def cleanup_number(number: str):
    number = number.replace("-", "")
    number = number.replace(" ", "")
    number = number.replace(".", "")
    number = "".join(char for char in number if char.isdigit())
    # we only need the last 4 digits of order number if more digis is provided
    return number[-4:] if len(number) > 4 else number


@func_description(
    "Check the order number provided is correct. This function must be called every time the user provides any number."
)
@func_parameter("order_number", "The number provided by user.")
@func_parameter(
    "full_order_number",
    "The user gave the FULL, 19 digit order number, instead of the last 6 digits. (Defaults to FALSE)",
)
def order_number_provided(
    conv: Conversation, flow: Flow, order_number: str, full_order_number: bool
):
    if full_order_number:
        order_number = order_number[-4:]

    conv.state.last_4_digits_order_number = cleanup_number(order_number)
    conv.log.info(
        "Collected last four digits of order number",
        order_number=conv.state.last_4_digits_order_number,
    )
    if not is_valid_last_4_digits(conv.state.last_4_digits_order_number):
        # Trying alternative transcripts
        for alternative in try_alternative_transcripts(conv, 4):
            conv.state.last_4_digits_order_number = cleanup_number(alternative)
            if is_valid_last_4_digits(conv.state.last_4_digits_order_number):
                conv.log.info(
                    "Trying alternative last 4 order number",
                    number=conv.state.last_4_digits_order_number,
                )
                break
        else:
            conv.write_metric("IDNV_LAST_6_DIGITS_INVALID")
            return ActionsIterator(
                "INVALID_LAST_FOUR_DIGITS_ACTIONS",
                [
                    {
                        "utterance": utterance(conv, "idnv_last4_invalid"),
                        "content": get_bullet_points(
                            "If the user provides their order number-even if it's same as before-immediately call the function order_number_provided."
                        ),
                    },
                    {
                        "utterance": utterance(conv, "idnv_order_not_found_transfer"),
                        "content": get_bullet_points(
                            "If the user provides their order number-even if it's same as before-immediately call the function order_number_provided.",
                            "If the user says 'yes', immediately call transfer_call with handoff_reason = 'IDNV_FAILED' and handoff_utterance = 'DEFAULT'",
                            "If the user says 'no' or 'no, thanks', immediately says: 'Can I have the last four digits of your order number again?'.",
                        ),
                    },
                ],
            ).get_next(conv)

    conv.write_metric("IDNV_LAST_6_DIGITS_COLLECTED", "True")
    return save_last_four_digits_order_number(conv, flow)


def save_last_four_digits_order_number(conv: Conversation, flow: Flow):
    if conv.state.order_from_full_order_number:
        if (
            conv.state.order_from_full_order_number.order_number[-4:]
            == conv.state.last_4_digits_order_number
        ):
            order_matched = conv.state.order_from_full_order_number

    elif conv.state.orders_from_phone_number:
        order_matched = next(
            (
                order
                for order in conv.state.orders_from_phone_number
                if order.order_number[-4:] == conv.state.last_4_digits_order_number
            ),
            None,
        )

    if not order_matched:
        flow.goto_step("Collect last 4")
        conv.write_metric("ORDER_NOT_FOUND")
        return ActionsIterator(
            "LAST_FOUR_DIGITS_ORDER_NOT_FOUND_ACTION",
            [
                {
                    "utterance": utterance(conv, "idnv_last4_mismatch"),
                    "content": get_bullet_points(
                        "If the user provides their order number — even if it's the same number as before — immediately call the function order_number_provided."
                    ),
                },
                {
                    "utterance": utterance(conv, "idnv_still_no_match_transfer"),
                    "content": get_bullet_points(
                        "If the user provides their order number — even if it's the same number as before — immediately call the function order_number_provided.",
                        "If the user says 'yes', immediately call transfer_call with handoff_reason = 'IDNV_FAILED' and handoff_utterance = 'DEFAULT'",
                        "If the user says 'no' or 'no, thanks', immediately says: 'Can I have the last four digits of your order number again?'.",
                    ),
                },
            ],
        ).get_next(conv)

    conv.write_metric("IDNV_LAST_6_DIGITS_MATCHED")

    conv.state.idnv_passed = True
    conv.write_metric("IDNV_SUCCESSFUL")

    conv.state.order_details = order_matched
    conv.write_metric("ORDER_FOUND")
    conv.write_metric("ORDER_NUMBER", order_matched.order_number)
    conv.write_metric("ORDER_STATUS", order_matched.order_status)

    # Reset Counter before entering next step
    conv.state.INVALID_LAST_FOUR_DIGITS_ACTIONS = None
    conv.state.LAST_FOUR_DIGITS_ORDER_NOT_FOUND_ACTION = None
    conv.state.in_idnv_flow = False
    conv.state.transfer_on_silence_loop = False
    conv.goto_flow("OMS_WISMO")
    return determine_order_status(conv, flow)
