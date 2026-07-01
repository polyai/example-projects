import re

from _gen import *  # <AUTO GENERATED>
from functions.mock_api import MockDispatchApi


def _is_valid_us_number(phone_number: str) -> bool:
    if not phone_number:
        return False
    pattern = r"^(?:\+1|1)?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"
    return bool(re.match(pattern, phone_number))


@func_description("**Call this function immediately at the start of the call**")
@func_latency_control(
    delay_before_responses_start=2,
    silence_after_each_response=2,
    delay_responses=[("[Ring]", 3), ("[Ring]", 3), ("[Ring]", 3)],
)
def initial_ani_lookup(conv: Conversation):
    conv.state.customer_found = False
    phone = conv.state.phone_number or conv.caller_number or ""
    conv.state.is_valid_number = _is_valid_us_number(phone)

    if conv.state.is_valid_number:
        try:
            customer = MockDispatchApi.lookup_customer_by_phone(phone)
            if customer:
                conv.state.customer_found = True
                conv.state.customer_details_list = [customer]
                conv.state.customer_id = customer["customerID"]
                conv.log.info("ANI match", customer_id=customer["customerID"])
            else:
                conv.write_metric("NO_ACCOUNT_FOUND_WITH_CALLER_ID", None)
        except Exception as e:
            conv.log.warning("ANI lookup error", error=e)
    else:
        conv.write_metric("INVALID_CALLER_ID", None)

    conv.exit_flow()
