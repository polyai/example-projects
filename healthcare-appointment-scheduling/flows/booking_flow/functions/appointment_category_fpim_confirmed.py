import plog
from _gen import *  # <AUTO GENERATED>

_EVENT_TYPE_CHECK_PROMPT = (
    "Review the conversation so far. Has the caller already explicitly stated a specific "
    "medical appointment type they want to book? Return exactly one of these values:\n"
    "- er_follow_up — ER or emergency room follow-up\n"
    "- hospital_follow_up — hospital or inpatient follow-up\n"
    "- recheck_diabetes — recheck or follow-up specifically for diabetes\n"
    "- recheck_hypertension — recheck or follow-up specifically for hypertension or blood pressure\n"
    "- recheck_medication — medication management or medication follow-up\n"
    "- recheck — recheck or follow-up for any other or unspecified condition\n"
    "- ill — sick visit, new illness, or new problem\n"
    "- unknown — appointment type is unclear or has not been stated yet\n\n"
    "IMPORTANT: Vague or general requests like 'checkup', 'general checkup', 'annual physical', "
    "'wellness visit', 'routine appointment', or just 'appointment' are NOT rechecks. "
    "Only return 'recheck' if the caller explicitly mentions a follow-up, recheck, or "
    "returning for a previously seen condition. When in doubt, return 'unknown'.\n\n"
    "Return only that single value, nothing else."
)

_VALID_EVENT_TYPES = {
    "er_follow_up",
    "hospital_follow_up",
    "recheck",
    "ill",
    "recheck_diabetes",
    "recheck_hypertension",
    "recheck_medication",
}


@func_description(
    "Called when the caller confirms they want to book a family practice, internal medicine, or primary care appointment. Sets the appointment category and either triggers identity verification or advances to event type collection if the caller is already identified."
)
def appointment_category_fpim_confirmed(conv: Conversation, flow: Flow) -> dict:
    log_prefix = "[appointment_category_fpim_confirmed]: "

    conv.state.booking_appointment_category = "fpim"
    conv.write_metric("BOOKING_TRIAGE_FPIM")

    identified = getattr(conv.state, "identified_patient", None)
    has_verified_id = isinstance(identified, dict) and bool(identified.get("id"))
    plog.info(f"{log_prefix} has_verified_id={has_verified_id}")

    if has_verified_id:
        plog.info(f"{log_prefix} patient already identified; loading insurance")
        from flows.booking_flow.function_steps.booking_entry import _load_insurance_and_route

        return _load_insurance_and_route(conv, flow)

    # Check if the caller already stated the appointment event type before IDNV so the
    # post-IDNV utterance can skip asking the question if it's already known.
    try:
        result = conv.utils.prompt_llm(_EVENT_TYPE_CHECK_PROMPT, show_history=True).strip().lower()
        pre_idnv_event_type = result if result in _VALID_EVENT_TYPES else None
    except Exception as e:
        conv.log.warning(
            "appointment_category_fpim_confirmed: event type pre-check failed", error=str(e)
        )
        pre_idnv_event_type = None

    conv.state.booking_pre_idnv_event_type = pre_idnv_event_type
    plog.info(f"{log_prefix} pre_idnv_event_type='{pre_idnv_event_type}'")

    conv.state.post_idnv_flow_name = "Booking Flow"
    plog.info(f"{log_prefix} set post_idnv_flow_name='Booking Flow'; goto_flow='IDNV'")
    conv.goto_flow("IDNV")
    is_cm = getattr(conv.state, "caller_is_case_manager", False)
    if is_cm:
        return {
            "utterance": (
                "I'll need to verify the patient's account before we can book an appointment. "
                "Is the number you're calling from the one we have on file for the patient?"
            )
        }
    return {
        "utterance": (
            "I'll need to verify your identity before we can book an appointment. "
            "Is the number you're calling from the one we have on file for you?"
        )
    }
