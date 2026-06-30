import plog
from _gen import *  # <AUTO GENERATED>
from functions.get_grace_nextgen_api_handler import (
    get_grace_nextgen_api_handler,
)
from functions.handoff import handoff


@func_latency_control(
    delay_before_responses_start=0,
    silence_after_each_response=3,
    delay_responses=[("typing_noise", 2), ("Just a second.", 3), ("typing_noise", 2)],
)
def save_collected_phone_and_lookup(conv: Conversation, flow: Flow):
    """Save collected phone to state, look up patients, then DOB or collect number."""
    log_prefix = "[save_collected_phone_and_lookup]: "
    phone_entity = conv.entities.phone_number.value if conv.entities.phone_number else None
    state_phone = getattr(conv.state, "idnv_collected_phone", None)
    plog.info(
        f"{log_prefix} phone_number_entity='{phone_entity}' state_phone='{state_phone}'",
        is_pii=True,
    )
    raw_source = None
    if phone_entity:
        raw_source = str(phone_entity).strip()
    elif state_phone:
        raw_source = str(state_phone).strip()
    if not raw_source:
        conv.log.warning("save_collected_phone_and_lookup: no phone number from entity or state")
        conv.exit_flow()
        return {
            "content": (
                "We didn't get a phone number. Offer to transfer them to "
                "someone who can look up their account."
            )
        }
    raw = raw_source
    digits = "".join(c for c in raw if c.isdigit())
    if len(digits) >= 10:
        conv.state.idnv_phone_number = digits[-10:] if len(digits) > 10 else digits
    else:
        conv.state.idnv_phone_number = raw
    conv.log.info(
        "IDNV using collected number",
        phone_last_digits=(
            conv.state.idnv_phone_number[-4:] if len(conv.state.idnv_phone_number) >= 4 else "***"
        ),
    )
    phone = conv.state.idnv_phone_number
    handler = get_grace_nextgen_api_handler(conv)
    try:
        patients = handler.lookup_patients(phone)
    except Exception as e:
        conv.log.error("IDNV lookup_patients failed", error=str(e))
        conv.write_metric("IDNV_FLOW_API_ERROR")
        return handoff(
            conv,
            reason="IDNV_API_FAILURE",
            utterance="Please hold while I transfer you to someone who can help.",
        )
    if not patients:
        # Clear stored phone so the LLM doesn't auto-resubmit the same number
        conv.state.idnv_collected_phone = None
        flow.goto_step("Collect Phone Number", "No Matching Phone Numbers")
        return {
            "content": (
                "That number didn't match an account. Ask if they have "
                "another number we could try, or offer to transfer."
            )
        }
    conv.state.idnv_candidate_patients = patients
    conv.write_metric("IDNV_CANDIDATES_FOUND", len(patients))
    conv.write_metric("IDNV_FLOW_PHONE_COLLECTED")
    ids = [p.id for p in patients]
    conv.log.info("IDNV candidates found", count=len(patients), person_ids=ids, is_pii=True)
    flow.goto_step("Collect Date of Birth", "Phone Number Matched")
    return {"content": ("Ask for their date of birth so we can confirm which account is theirs.")}
