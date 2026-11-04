from _gen import *  # <AUTO GENERATED>
from functions import appointments
from functions.handoff import handoff

DISABLED_UTTERANCE = "For cancellations I'll need to put you through to our scheduling team. One moment, please."


@func_description("The caller wants to cancel an existing appointment.")
def start_cancellation_flow(conv: Conversation):
    conv.write_metric("PRIMARY_INTENT", "CANCEL_APPOINTMENT")
    settings = (conv.real_time_config or {}).get("settings", {})
    if not settings.get("cancel_appointment_flow_enabled", True):
        return handoff(conv, "CANCEL_APPOINTMENT", DISABLED_UTTERANCE)
    appointments.forget_readback(conv, "cancel")
    gate = appointments.gate(conv, "cancel_appointment")
    if gate:
        return gate
    conv.goto_flow("cancel_appointment")
    return "CANCEL: the caller is verified. Carry on with the cancellation."
