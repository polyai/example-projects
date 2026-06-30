import plog
from _gen import *  # <AUTO GENERATED>
from functions.get_grace_nextgen_api_handler import get_grace_nextgen_api_handler

_HOSPITAL_ER_TYPES = {"er_follow_up", "hospital_follow_up"}
_INS_LOG = "[booking_entry.load_insurance]: "
_ALERT_LOG = "[booking_entry.check_alerts]: "


def _load_insurance_and_route(conv: Conversation, flow: Flow) -> dict:
    """Load patient insurance from chart and route to the appropriate insurance step."""
    identified = getattr(conv.state, "identified_patient", None)
    person_id = identified.get("id") if isinstance(identified, dict) else None

    if not person_id:
        plog.info(f"{_INS_LOG} no person_id; skipping insurance check")
        flow.goto_step("Collect Appointment Event Type", "No patient ID for insurance lookup")
        return {"content": "Ask the caller what type of appointment they would like to book."}

    try:
        handler = get_grace_nextgen_api_handler(conv)
        insurances = handler.get_person_insurances(person_id)
        active = [
            i
            for i in insurances
            if getattr(i, "is_active", False) and not getattr(i, "is_deleted", False)
        ]
    except Exception as e:
        conv.log.error(f"{_INS_LOG} insurance lookup failed", error=str(e))
        conv.write_metric("INSURANCE_LOOKUP_API_ERROR")
        plog.info(f"{_INS_LOG} API error; skipping insurance check")
        flow.goto_step("Collect Appointment Event Type", "Insurance API error — skipping check")
        return {"content": "Ask the caller what type of appointment they would like to book."}

    is_cm = getattr(conv.state, "caller_is_case_manager", False)

    if active:
        active.sort(
            key=lambda ins: ins.default_cob if ins.default_cob is not None else float("inf")
        )
        primary = active[0]
        conv.state.insurance_on_file_payer_name = primary.payer_name
        conv.state.insurance_on_file_payer_id = primary.payer_id
        conv.state.insurance_all_active = [
            {"payer_name": ins.payer_name, "payer_id": ins.payer_id} for ins in active
        ]
        conv.write_metric("INSURANCE_FOUND_ON_CHART")
        plog.info(
            f"{_INS_LOG} found {len(active)} active insurance(s); "
            f"primary='{primary.payer_name}'; goto_step='Confirm Insurance'",
            is_pii=True,
        )
        flow.goto_step("Confirm Insurance", "Insurance found on chart")
        if is_cm:
            return {
                "utterance": (
                    f"I can see the patient has {primary.payer_name} on file. "
                    "Is that still their current insurance?"
                )
            }
        return {
            "utterance": (
                f"I can see you have {primary.payer_name} on file. "
                "Is that still your current insurance?"
            )
        }

    conv.write_metric("INSURANCE_NOT_ON_CHART")
    plog.info(f"{_INS_LOG} no active insurance found; goto_step='Collect Insurance Name'")
    flow.goto_step("Collect Insurance Name", "No insurance on chart")
    if is_cm:
        return {
            "utterance": (
                "I don't see any insurance on file for the patient. "
                "What insurance plan do they have?"
            )
        }
    return {
        "utterance": "I don't see any insurance on file for you. What insurance plan do you have?"
    }


def booking_entry(conv: Conversation, flow: Flow):
    """Entry routing for the Booking Flow."""

    log_prefix = "[booking_entry]: "

    category = getattr(conv.state, "booking_appointment_category", None)
    identified = getattr(conv.state, "identified_patient", None)
    has_verified_id = isinstance(identified, dict) and bool(identified.get("id"))
    pre_event_type = getattr(conv.state, "booking_pre_idnv_event_type", None)

    plog.info(
        f"{log_prefix} booking_appointment_category='{category}'"
        f" has_verified_id={has_verified_id}"
        f" pre_event_type='{pre_event_type}'"
    )

    if category == "fpim" and has_verified_id:
        conv.state.booking_alerts_checked = True

        if pre_event_type in _HOSPITAL_ER_TYPES:
            facility_label = "emergency room" if pre_event_type == "er_follow_up" else "hospital"
            conv.state.booking_appointment_type = pre_event_type
            conv.state.booking_facility_type_label = facility_label
            conv.write_metric("BOOKING_FLOW_TYPE_CONFIRMED", pre_event_type)

        insurance_already_verified = getattr(conv.state, "insurance_verified_plan", None)
        if insurance_already_verified:
            plog.info(
                f"{log_prefix} insurance already verified ('{insurance_already_verified}'); "
                "skipping insurance check to prevent re-entry loop"
            )
            flow.goto_step("Collect Appointment Event Type")
            return {"content": "Ask the caller what type of appointment they would like to book."}

        plog.info(f"{log_prefix} post-IDNV return; loading insurance")
        return _load_insurance_and_route(conv, flow)

    caller_type_known = getattr(conv.state, "caller_is_case_manager", None) is not None
    if caller_type_known:
        plog.info(f"{log_prefix} fresh entry (caller type known); goto_step='Check New Patient'")
        flow.goto_step(
            "Check New Patient",
            "Fresh booking entry — caller type already known",
        )
        return {
            "content": ("Check whether the caller is a new or existing patient at Poly Clinic.")
        }

    plog.info(f"{log_prefix} fresh entry; goto_step='Collect Caller Type'")
    flow.goto_step(
        "Collect Caller Type",
        "Fresh booking entry — collect caller type first",
    )
    return {"content": "Ask whether the caller is a patient or a case manager."}
