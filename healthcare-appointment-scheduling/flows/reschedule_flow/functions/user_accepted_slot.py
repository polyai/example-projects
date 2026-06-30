from typing import Any

import plog
from _gen import *  # <AUTO GENERATED>
from functions.nextgen_response_models import AppointmentSlot


@func_description(
    "Called when the user accepts the offered appointment slot; transitions to collect the reschedule reason before executing the API call."
)
def user_accepted_slot(conv: Conversation, flow: Flow) -> dict[str, Any]:
    """Validate the accepted slot is usable, then transition to collect reschedule reason."""
    log_prefix = "[user_accepted_slot.user_accepted_slot]: "
    plog.info(f"{log_prefix} flow_current_step={getattr(flow, 'current_step', None)!r}")

    appointment_id = getattr(conv.state, "reschedule_target_appointment_id", None)
    offered_slot_data = getattr(conv.state, "reschedule_offered_slot", None)

    if not appointment_id:
        plog.info(f"{log_prefix} missing reschedule_target_appointment_id; exiting")
        conv.log.error("user_accepted_slot: no reschedule_target_appointment_id on state")
        conv.exit_flow()
        return {"utterance": "We couldn't complete the rescheduling. Please try again later."}

    if not offered_slot_data:
        plog.info(f"{log_prefix} missing reschedule_offered_slot; exiting")
        conv.log.error("user_accepted_slot: no reschedule_offered_slot on state")
        conv.exit_flow()
        return {"utterance": "We couldn't complete the rescheduling. Please try again later."}

    slot = AppointmentSlot.model_validate(offered_slot_data)
    ap_last4 = str(appointment_id)[-4:] if len(str(appointment_id)) >= 4 else "****"
    plog.info(
        f"{log_prefix} appointment_id_last4='{ap_last4}' "
        f"slot_start='{slot.start_date}' location_id='{slot.location_id}'",
        is_pii=True,
    )

    if not slot.start_date or not slot.duration_minutes:
        plog.info(f"{log_prefix} slot missing required fields; exiting")
        conv.log.error(
            "user_accepted_slot: offered slot missing start_date or duration_minutes",
            slot_start=str(slot.start_date),
            slot_duration=str(slot.duration_minutes),
            is_pii=True,
        )
        conv.exit_flow()
        return {"utterance": "We couldn't complete the rescheduling. Please try again later."}

    plog.info(f"{log_prefix} slot confirmed; transitioning to Collect Reschedule Reason")
    flow.goto_step("Collect Reschedule Reason")
    is_cm = getattr(conv.state, "caller_is_case_manager", False)
    if is_cm:
        return {
            "utterance": "Before I confirm that, could you tell me the reason the patient needs to reschedule?"
        }
    return {
        "utterance": "Before I confirm that, could you tell me the reason you need to reschedule?"
    }
