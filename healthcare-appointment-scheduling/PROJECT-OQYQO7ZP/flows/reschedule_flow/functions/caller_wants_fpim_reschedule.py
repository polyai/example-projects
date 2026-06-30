import plog
from _gen import *  # <AUTO GENERATED>
from functions.load_reschedule_upcoming_appointments import (
    load_reschedule_upcoming_appointments_for_state,
)


@func_description(
    "Called when the caller confirms they want to reschedule a family practice, internal medicine, or primary care appointment. Verifies identity if needed, then advances to appointment resolution."
)
def caller_wants_fpim_reschedule(conv: Conversation, flow: Flow) -> dict:
    log_prefix = "[caller_wants_fpim_reschedule.caller_wants_fpim_reschedule]: "

    conv.state.reschedule_triage_done = True
    conv.write_metric("RESCHEDULE_TRIAGE_FPIM")

    identified = getattr(conv.state, "identified_patient", None)
    has_verified_id = isinstance(identified, dict) and bool(identified.get("id"))
    plog.info(f"{log_prefix} has_verified_patient_id={has_verified_id}")

    if has_verified_id:
        preload = load_reschedule_upcoming_appointments_for_state(conv)
        if not preload.ok:
            plog.info(f"{log_prefix} reschedule preload failed; offering to schedule instead")
            conv.exit_flow()
            return {
                "utterance": preload.utterance,
                "content": (
                    "No upcoming appointments were found. The caller may have missed their "
                    "appointment. If the caller says yes to scheduling a new appointment, "
                    "call {{fn:start_booking_flow}}. If they say no or want something else, "
                    "ask how else you can help."
                ),
            }
        plog.info(f"{log_prefix} appointments preloaded, goto_step='Resolve Appointment'")
        flow.goto_step("Resolve Appointment")
        return {"content": "Ask the caller which appointment they would like to reschedule."}

    conv.state.post_idnv_flow_name = "Reschedule Flow"
    plog.info(f"{log_prefix} not identified, goto_flow='IDNV'")
    conv.goto_flow("IDNV")
    is_cm = getattr(conv.state, "caller_is_case_manager", False)
    if is_cm:
        return {
            "utterance": (
                "I'll need to verify the patient's account before we can reschedule an appointment. "
                "Is the number you're calling from the one we have on file for the patient?"
            )
        }
    return {
        "utterance": (
            "I'll need to verify your identity before we can reschedule an appointment. "
            "Is the number you're calling from the one we have on file for you?"
        )
    }
