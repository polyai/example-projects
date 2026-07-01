import json

from _gen import *  # <AUTO GENERATED>
from functions.make_booking_utils import check_cancellation_policy


@func_description("User has selected the price options to book for different people in the group")
@func_parameter(
    "prices_list",
    'list of prices as an escaped JSON string, e.g. "[{\\"id\\": 123, \\"count\\": 1}, {\\"price_id\\": 456\\", \\"count\\": 2}]"',
)
def experience_prices_selected(conv: Conversation, flow: Flow, prices_list: str):
    total_count = 0
    price_id_to_details = {}
    conv.state.total_price = 0
    for entry in conv.state.experience_price_options or []:
        price_id_to_details[entry["price_id"]] = entry
    try:
        corrected_str = prices_list.replace('\\"', '"')
        selected_prices = json.loads(corrected_str)
        if not isinstance(selected_prices, list) and all(
            isinstance(x, dict) for x in selected_prices
        ):
            return "prices_list contains some non-dictionary values"
        for price_selection in selected_prices:
            if price_selection["price_id"] not in price_id_to_details:
                return f"{price_selection} uses and invalid price id"
            total_count += price_selection["count"]
            conv.state.total_price += (
                price_id_to_details[price_selection["price_id"]]["min_unit_amount"]
                * price_selection["count"]
            )
    except (ValueError, SyntaxError):
        return "prices_list is not a valid list."
    if total_count != conv.state.party_size:
        return f"The count for each price ({total_count}) don't add up to total party size ({conv.state.party_size})"
    conv.state.party_size_per_price_type = []
    for price in selected_prices:
        conv.state.party_size_per_price_type.append(
            {"id": price["price_id"], "count": price["count"]}
        )
    return check_cancellation_policy(
        conv,
        flow,
        conv.state.datetime_str,
        conv.state.experience_id,
        date=conv.state.date,
        time=conv.state.time,
        party_size=conv.state.party_size,
    )
