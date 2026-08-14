from _gen import *  # <AUTO GENERATED>
import plog
from functions.get_grace_nextgen_api_handler import (
    get_grace_nextgen_api_handler,
)
from functions.handoff import handoff


def save_caller_phone_and_lookup(conv: Conversation, flow: Flow):
    """Save caller phone to state, look up patients, then go to DOB or collect number."""
    log_prefix = "[save_caller_phone_and_lookup]: "
    plog.info(f"{log_prefix} caller_number='{conv.caller_number}'", is_pii=True)

    # Prefer phone_number entity when set: user gave digits and then confirmed (e.g. "yeah" to
    # "Is 404-… the number on file?"). Chat caller_id may be an email; the entity is the real key.
    raw: str | None = None
    if conv.entities.phone_number:
        raw = str(conv.entities.phone_number.value).strip()
        plog.info(f"{log_prefix} lookup_source=phone_number_entity")
    elif conv.caller_number:
        raw = str(conv.caller_number).strip()
        plog.info(f"{log_prefix} lookup_source=caller_number")
    else:
        conv.log.warning(
            "save_caller_phone_and_lookup: no phone_number entity and no caller_number"
        )
        conv.exit_flow()
        return {
            "content": (
                "We couldn't detect the number they're calling from. "
                "Ask for the phone number on file or offer to transfer."
            )
        }

    digits = "".join(c for c in raw if c.isdigit())
    if len(digits) >= 10:
        conv.state.idnv_phone_number = digits[-10:] if len(digits) > 10 else digits
    else:
        conv.state.idnv_phone_number = raw
    lookup_src = (
        "phone_number_entity" if conv.entities.phone_number else "caller_number"
    )
    conv.log.info(
        "IDNV phone for lookup",
        source=lookup_src,
        phone_last_digits=(
            conv.state.idnv_phone_number[-4:]
            if len(conv.state.idnv_phone_number) >= 4
            else "***"
        ),
    )
    phone = conv.state.idnv_phone_number
    try:
        handler = get_grace_nextgen_api_handler(conv)
        patients = handler.lookup_patients(phone)
    except Exception as e:
        conv.log.error("IDNV lookup_patients failed", error=str(e))
        conv.write_metric("IDNV_FLOW_API_ERROR", True)
        return handoff(
            conv,
            reason="IDNV_API_FAILURE",
            utterance="Please hold while I transfer you to someone who can help.",
        )
    if not patients:
        flow.goto_step("Collect Phone Number", "No Account with That Phone")
        return {
            "content": (
                "No account with that number. Ask if there's another phone number we could try."
            )
        }
    conv.state.idnv_candidate_patients = patients
    conv.write_metric("IDNV_CANDIDATES_FOUND", len(patients))
    conv.write_metric("IDNV_FLOW_PHONE_COLLECTED", True)
    ids = [p.id for p in patients]
    conv.log.info(
        "IDNV candidates found", count=len(patients), person_ids=ids, is_pii=True
    )
    flow.goto_step("Collect Date of Birth", "Phone number collected")
    return {
        "content": (
            "Ask for their date of birth so we can confirm which account is theirs."
        )
    }
