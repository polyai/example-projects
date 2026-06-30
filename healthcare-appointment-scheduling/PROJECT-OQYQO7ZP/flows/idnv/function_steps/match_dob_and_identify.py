from datetime import date

import plog
from _gen import *  # <AUTO GENERATED>
from functions.handoff import handoff

_MINOR_AGE_THRESHOLD = 18


def _normalize_dob(value) -> str | None:
    """Return YYYY-MM-DD string from entity value (date object or string)."""
    import re

    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    digits = re.sub(r"\D", "", s)
    if len(digits) == 8:
        y1 = int(digits[:4])
        if 1900 <= y1 <= 2100:
            return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"
        return f"{digits[4:8]}-{digits[:2]}-{digits[2:4]}"
    return s[:10] if len(s) >= 10 else s


def _patient_dob_string(p) -> str:
    """Date of birth from API dict or Person model."""
    if isinstance(p, dict):
        raw = p.get("dateOfBirth") or p.get("date_of_birth") or ""
    else:
        raw = getattr(p, "date_of_birth", None) or getattr(p, "dateOfBirth", None) or ""
    return str(raw).strip() if raw else ""


def _patient_id(p):
    """Person id from dict or model (for logging)."""
    if isinstance(p, dict):
        return p.get("id")
    return getattr(p, "id", None)


def _patient_to_state_dict(p) -> dict:
    """Normalize API person (dict or Pydantic Person) for conv.state.identified_patient."""
    if isinstance(p, dict):
        return p
    if hasattr(p, "model_dump"):
        return p.model_dump(mode="json", by_alias=True)
    pid = _patient_id(p)
    return {"id": pid} if pid else {}


@func_latency_control(
    delay_before_responses_start=0,
    silence_after_each_response=3,
    delay_responses=[("typing_noise", 2), ("One moment.", 3)],
)
def match_dob_and_identify(conv: Conversation, flow: Flow):
    """Match DOB to candidate patients; save identified patient or hand off."""
    log_prefix = "[match_dob_and_identify]: "
    candidates = getattr(conv.state, "idnv_candidate_patients", None) or []
    plog.info(f"{log_prefix} candidate_count={len(candidates)}")
    if not candidates:
        plog.info(f"{log_prefix} no idnv_candidate_patients; handoff IDNV_NO_CANDIDATES")
        conv.log.warning("match_dob_and_identify called but no idnv_candidate_patients")
        conv.state.post_idnv_flow_name = None
        conv.write_metric("IDNV_NO_MATCHES")
        return handoff(
            conv,
            reason="IDNV_NO_CANDIDATES",
            utterance="Please hold while I transfer you to someone who can help.",
        )
    dob_value = conv.entities.date_of_birth.value if conv.entities.date_of_birth else None
    dob_norm = _normalize_dob(dob_value)
    if not dob_norm:
        plog.info(f"{log_prefix} no date_of_birth entity; handoff IDNV_NO_DOB")
        conv.log.warning("match_dob_and_identify called but no date_of_birth entity")
        conv.state.post_idnv_flow_name = None
        conv.write_metric("IDNV_DOB_NOT_COLLECTED")
        return handoff(
            conv,
            reason="IDNV_COLLECTION_FAILED",
            utterance="Please hold while I transfer you to someone who can help.",
        )
    matches = []
    for p in candidates:
        api_dob = _patient_dob_string(p)
        if not api_dob:
            continue
        api_norm = api_dob[:10] if len(api_dob) >= 10 else api_dob
        if api_norm == dob_norm:
            matches.append(p)
    candidate_person_ids = [_patient_id(p) for p in candidates]
    plog.info(
        f"{log_prefix} dob_norm='{dob_norm}', match_count={len(matches)}, "
        f"candidate_person_ids={candidate_person_ids!r}",
        is_pii=True,
    )
    if len(matches) == 0:
        dob_attempts = (getattr(conv.state, "idnv_dob_attempts", None) or 0) + 1
        conv.state.idnv_dob_attempts = dob_attempts
        plog.info(
            f"{log_prefix} IDNV no DOB match dob_norm='{dob_norm}' candidate_count={len(candidates)}"
            f" dob_attempts={dob_attempts}",
            is_pii=True,
        )
        conv.log.info(
            "IDNV no DOB match",
            dob_norm=dob_norm,
            candidate_count=len(candidates),
            dob_attempts=dob_attempts,
            is_pii=True,
        )
        if dob_attempts >= 3:
            conv.state.post_idnv_flow_name = None
            conv.write_metric("IDNV_PATIENT_NOT_FOUND")
            return handoff(
                conv,
                reason="IDNV_NO_MATCH",
                utterance="We couldn't match that date of birth to an account. "
                "Let me transfer you to someone who can help.",
            )
        flow.goto_step("Collect Date of Birth", "Retry Collect DOB")
        return {
            "content": ("Tell the user that date of birth didn't match — ask them to try again.")
        }
    if len(matches) > 1:
        plog.info(
            f"{log_prefix} IDNV multiple DOB matches dob_norm='{dob_norm}' match_count={len(matches)}",
            is_pii=True,
        )
        conv.log.info(
            "IDNV multiple DOB matches",
            dob_norm=dob_norm,
            match_count=len(matches),
            is_pii=True,
        )
        conv.state.post_idnv_flow_name = None
        conv.write_metric("IDNV_PATIENT_AMBIGUOUS")
        return handoff(
            conv,
            reason="IDNV_NO_MATCH",
            utterance="We found more than one account matching that information. "
            "Let me transfer you to someone who can help.",
        )
    matched = matches[0]
    conv.state.identified_patient = _patient_to_state_dict(matched)
    conv.write_metric("IDNV_DOB_CONFIRMED")
    conv.write_metric("IDNV_FLOW_DOB_COLLECTED")
    _pid = _patient_id(matched)
    plog.info(f"{log_prefix} IDNV identified patient person_id={_pid!r}", is_pii=True)

    # Check if patient is a minor (under 18)
    try:
        dob_date = date.fromisoformat(dob_norm)
        today = date.today()
        age = (
            today.year - dob_date.year - ((today.month, today.day) < (dob_date.month, dob_date.day))
        )
        plog.info(f"{log_prefix} patient_age={age}", is_pii=True)
        if age < _MINOR_AGE_THRESHOLD:
            plog.info(f"{log_prefix} patient is a minor (age={age}); handing off", is_pii=True)
            conv.write_metric("IDNV_MINOR_DETECTED")
            conv.state.post_idnv_flow_name = None
            return handoff(
                conv,
                reason="IDNV_MINOR",
                utterance=(
                    "Since this appointment is for a minor, I'll need to transfer you "
                    "to someone who can help. Please hold while I put you through."
                ),
            )
    except (ValueError, TypeError):
        plog.info(
            f"{log_prefix} could not parse DOB for age check dob_norm='{dob_norm}'", is_pii=True
        )

    _pid_last4 = str(_pid)[-4:] if _pid and len(str(_pid)) >= 4 else "****"
    pending = getattr(conv.state, "post_idnv_flow_name", None)
    plog.info(
        f"{log_prefix} identified patient_id_last4='{_pid_last4}' post_idnv_flow_name='{pending}'"
    )

    flow.goto_step("Collect Name", "Account Found, Check Name")
    return {
        "content": (
            "Tell the user you found an account matching their phone "
            "and date of birth, and to confirm it's them, ask for the "
            "name we have on file for this account."
        )
    }
