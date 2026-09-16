from _gen import *  # <AUTO GENERATED>
import re
import unicodedata

import plog
from functions.handoff import handoff


def _ascii_lower(value) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    return text.encode("ascii", "ignore").decode().lower()


def account_name_parts(patient) -> tuple[str, str]:
    if isinstance(patient, dict):
        first = patient.get("first_name") or patient.get("firstName") or ""
        last = patient.get("last_name") or patient.get("lastName") or ""
    else:
        first = (
            getattr(patient, "first_name", None)
            or getattr(patient, "firstName", None)
            or ""
        )
        last = (
            getattr(patient, "last_name", None)
            or getattr(patient, "lastName", None)
            or ""
        )
    return str(first).strip(), str(last).strip()


def account_display_name(patient) -> str:
    first, last = account_name_parts(patient)
    return f"{first} {last}".strip() or "Unknown"


def deterministic_name_match(
    stated, first: str, last: str, require_both: bool = False
) -> bool:
    words = [t for t in re.split(r"[^a-z]+", _ascii_lower(stated)) if t]
    tokens = {t for t in words if len(t) > 1}
    # only runs of single letters count as spelling, so short names cannot match inside ordinary words
    spelled, run = set(), ""
    for word in words:
        if len(word) == 1:
            run += word
            continue
        if run:
            spelled.add(run)
        run = ""
    if run:
        spelled.add(run)
    keys = [_ascii_lower(first), _ascii_lower(last)]
    if all(keys) and {keys[0] + keys[1], keys[1] + keys[0]} & tokens:
        return True
    hits = [
        len(key) >= 2 and (key in tokens or any(key in s for s in spelled))
        for key in keys
    ]
    return all(hits) if require_both else any(hits)


def handle_name_matched(conv, log_prefix: str):
    conv.write_metric("IDNV_FLOW_NAME_COLLECTED", True)
    conv.write_metric("IDNV_FLOW_COMPLETED", True)
    conv.write_metric("IDNV_IDENTIFIED", True)

    pending = getattr(conv.state, "post_idnv_flow_name", None)
    plog.info(f"{log_prefix} name matched; post_idnv_flow_name='{pending}'")

    if pending:
        conv.state.post_idnv_flow_name = None
        conv.goto_flow(pending)
        return {
            "utterance": "Thanks for verifying your identity. Let me pull up the details."
        }

    conv.exit_flow()
    return {
        "content": (
            "Tell the user you've confirmed their account and ask how you can help them today."
        )
    }


@func_description("Called when the caller has spelled their name for verification.")
def match_spelled_name_to_account(conv: Conversation):
    log_prefix = "[match_spelled_name_to_account]: "
    patient = getattr(conv.state, "identified_patient", None)
    if not patient:
        return handoff(
            conv,
            reason="IDNV_NAME_MATCH_NO_ACCOUNT",
            utterance="Please hold while I transfer you to someone who can help.",
        )

    first, last = account_name_parts(patient)
    account_name = f"{first} {last}".strip() or "Unknown"
    candidates = getattr(conv.state, "idnv_candidate_patients", None) or []
    is_match = deterministic_name_match(
        f"{conv.transcript_alternatives}", first, last, require_both=len(candidates) > 1
    )
    llm_response = ""

    if not is_match:
        prompt = (
            "You are a name matcher for identity verification. The caller's FIRST "
            "spoken name did not match, so they were asked to spell or repeat their "
            "name. You must now evaluate ONLY the caller's SECOND attempt.\n\n"
            "IMPORTANT: Completely IGNORE the first name the caller gave earlier.\n\n"
        )
        if len(candidates) <= 1:
            prompt += (
                "IMPORTANT CONTEXT: The caller's phone number and date of birth "
                "have ALREADY been verified and uniquely match this account. "
                "Be very generous -- a match on first name OR last name alone is sufficient.\n\n"
            )
        prompt += (
            "The caller may have spelled letters or said the name normally.\n"
            "Allow ASR errors, homophones, and nicknames.\n\n"
            f"Account name on file:\n{account_name!r}\n\n"
            f"Transcript alternatives (from ASR): \n{conv.transcript_alternatives}\n\n"
            "OUTPUT FORMAT:\nReturn ONLY one word: match or no_match"
        )

        result = None
        try:
            result = conv.utils.prompt_llm(prompt, show_history=True)
        except Exception as e:
            conv.log.warning(
                "match_spelled_name_to_account: prompt_llm failed, using deterministic fallback",
                error=str(e),
            )
        llm_response = str(result or "").strip()
        is_match = llm_response.lower() == "match"

    conv.log.info(
        "IDNV spelled name match result",
        account_name=account_name,
        is_match=is_match,
        llm_response=llm_response[:50],
        is_pii=True,
    )

    if not is_match:
        return handoff(
            conv,
            reason="IDNV_NAME_NO_MATCH",
            utterance=(
                "I still wasn't able to match that to the account. "
                "Let me transfer you to someone who can help."
            ),
        )

    return handle_name_matched(conv, log_prefix)
