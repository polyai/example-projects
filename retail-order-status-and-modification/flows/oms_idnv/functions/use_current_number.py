from _gen import *  # <AUTO GENERATED>
from functions.step_utils import is_ca_from_orders
from functions.utterances import utterance

SUPPORTED_COUNTRIES = {"US", "CA"}


@func_description("Transition to step billing zipcode/postcode collection.")
def use_current_number(conv: Conversation, flow: Flow):
    conv.state.using_calling_number = True
    conv.state.using_phone_number = True
    candidates = getattr(conv.state, "orders_from_phone_number", None) or []

    if not conv.real_time_config.get("ignore_international_billing_zip_handoff_for_testing"):
        international = next(
            (
                o
                for o in candidates
                if getattr(o, "billing_country_code", "US") not in SUPPORTED_COUNTRIES
            ),
            None,
        )
        if international:
            conv.write_metric("IDNV_INTERNATIONAL_BILLING_ZIP")
            return conv.functions.transfer_call(
                "DEFAULT",
                "INTERNATIONAL_BILLING_ZIP",
                utterance(conv, "idnv_international_zip"),
            )

    is_ca = is_ca_from_orders(conv, candidates)

    if is_ca:
        conv.say(utterance(conv, "idnv_ask_billing_postcode"))
        flow.goto_step("Collect billing postcode")
    else:
        conv.say(utterance(conv, "idnv_ask_billing_zipcode"))
        flow.goto_step("Collect billing zipcode")
