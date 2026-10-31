from _gen import *  # <AUTO GENERATED>
from functions import idnv
from functions.handoff import handoff


@func_description(
    "The caller asks to cancel an existing visit. Not for an 'okay' to something you offered."
)
def start_cancel_appointment(conv: Conversation):
    conv.write_metric("PRIMARY_INTENT", "CANCEL_APPOINTMENT")
    settings = (conv.real_time_config or {}).get("settings", {})
    if not settings.get("cancel_appointment_flow_enabled", True):
        return handoff(
            conv,
            "CANCEL_APPOINTMENT",
            "For cancellations I'll need to put you through to a colleague. One moment please.",
            "CUSTOMER_CARE",
        )
    gate = idnv.require(conv, "cancel_appointment")
    if gate:
        return gate
    conv.goto_flow("cancel_appointment")
