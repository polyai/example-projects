import plog
from _gen import *  # <AUTO GENERATED>
from functions.load_cancel_upcoming_appointments import load_cancel_upcoming_appointments_for_state


@func_description(
    "Called when the caller confirms they want to cancel a family practice, internal medicine, or primary care appointment. Verifies identity if needed, then advances to appointment resolution."
)
def caller_wants_fpim_cancel(conv: Conversation, flow: Flow) -> dict:
    log_prefix = "[caller_wants_fpim_cancel.caller_wants_fpim_cancel]: "

    conv.state.cancel_triage_done = True
    conv.write_metric("CANCEL_TRIAGE_FPIM")

    identified = getattr(conv.state, "identified_patient", None)
    has_verified_id = isinstance(identified, dict) and bool(identified.get("id"))
    plog.info(f"{log_prefix} has_verified_patient_id={has_verified_id}")

    if has_verified_id:
        preload = load_cancel_upcoming_appointments_for_state(conv)
        if not preload.ok:
            plog.info(f"{log_prefix} cancel preload failed")
            return {"utterance": preload.utterance}
        plog.info(f"{log_prefix} appointments preloaded, goto_step='Resolve Appointment'")
        flow.goto_step("Resolve Appointment")
        return {"content": "Ask the caller which appointment they would like to cancel."}

    conv.state.post_idnv_flow_name = "Cancel Flow"
    plog.info(f"{log_prefix} not identified, goto_flow='IDNV'")
    conv.goto_flow("IDNV")
    is_cm = getattr(conv.state, "caller_is_case_manager", False)
    if is_cm:
        return {
            "utterance": (
                "I'll need to verify the patient's account before we can cancel an appointment. "
                "Is the number you're calling from the one we have on file for the patient?"
            )
        }
    return {
        "utterance": (
            "I'll need to verify your identity before we can cancel an appointment. "
            "Is the number you're calling from the one we have on file for you?"
        )
    }
