from _gen import *  # <AUTO GENERATED>
from functions.start_function import set_datetime


@func_description("Handle bookings that are larger or equal to the party size limit")
@func_parameter("party_size", "Party size for the booking")
def start_handle_over_max_group_size(conv: Conversation, party_size: int):
    # add a check in case this was called with a smaller group size
    if party_size < int(conv.variant.large_party_size):
        set_datetime(conv)
        if conv.current_flow not in ["make_booking", "confirm_cancel_modify_booking"]:
            conv.goto_flow("make_booking")
        return "The group size is under the maximum, this function shouldn't have been called, proceed with booking as normal"
    else:
        transfer_utterance = conv.real_time_config.get("large_party_transfers", {}).get(
            "transfer_utterance"
        )
        transfer_destination = conv.real_time_config.get(
            "large_party_transfers", {}
        ).get("transfer_destination")

        conv.write_metric("LARGE_PARTY_COVERS", party_size)
        sms_instruction = (
            f"If the user accepts the SMS offer, call start_sms_flow with template_id='large_party'. "
            f"If the user declines the SMS offer, call try_transfer_call function with "
            f"handoff_reason = restaurant_max_group_size "
            f"transfer_utterance = {transfer_utterance} "
            f"transfer_destination = {transfer_destination}."
        )
        return {
            "utterance": (
                "For bookings of that size, you’ll need to fill out the group booking form on "
                "our website. Would you like me to send you the link?"
            ),
            "content": sms_instruction,
        }
