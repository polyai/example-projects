from _gen import *  # <AUTO GENERATED>
from functions import idnv
from functions.handoff import handoff


@func_description("The caller wants to cancel an existing appointment.")
def start_cancellation_flow(conv: Conversation):
    conv.write_metric("PRIMARY_INTENT", "CANCEL_APPOINTMENT")
    settings = (conv.real_time_config or {}).get("settings", {})
    if not settings.get("cancel_appointment_flow_enabled", True):
        return handoff(
            conv,
            "CANCEL_APPOINTMENT",
            "For cancellations I'll need to put you through to our scheduling team. One moment "
            "please.",
        )
    gate = idnv.require(conv, "cancel_appointment", strength=idnv.STRICT)
    if gate:
        return gate
    conv.goto_flow("cancel_appointment")
