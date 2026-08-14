"""Name-match verification for IDNV flow. After match, routes to the pending flow."""

from _gen import *  # <AUTO GENERATED>
import plog
from functions.handoff import handoff

_POST_IDNV_CANCEL_FLOW = "Cancel Flow"
_POST_IDNV_RESCHEDULE_FLOW = "Reschedule Flow"
_POST_IDNV_BOOKING_FLOW = "Booking Flow"


def account_display_name(patient) -> str:
    """Return a display name from the patient dict/object."""
    if isinstance(patient, dict):
        first = (patient.get("first_name") or patient.get("firstName") or "").strip()
        last = (patient.get("last_name") or patient.get("lastName") or "").strip()
    else:
        first = (
            getattr(patient, "first_name", None)
            or getattr(patient, "firstName", None)
            or ""
        ).strip()
        last = (
            getattr(patient, "last_name", None)
            or getattr(patient, "lastName", None)
            or ""
        ).strip()
    return f"{first} {last}".strip() or "Unknown"


def handle_name_matched(conv, log_prefix: str):
    """Shared post-match logic: set state and route to the pending flow."""
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

    account_name = account_display_name(patient)

    candidates = getattr(conv.state, "idnv_candidate_patients", None) or []
    single_dob_match = len(candidates) <= 1

    prompt = (
        "You are a name matcher for identity verification. The caller's FIRST "
        "spoken name did not match, so they were asked to spell or repeat their "
        "name. You must now evaluate ONLY the caller's SECOND attempt.\n\n"
        "IMPORTANT: Completely IGNORE the first name the caller gave earlier.\n\n"
    )

    if single_dob_match:
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

    try:
        result = conv.utils.prompt_llm(prompt, show_history=True)
    except Exception as e:
        conv.log.error("match_spelled_name_to_account prompt_llm failed", error=str(e))
        return handoff(
            conv,
            reason="IDNV_NAME_MATCH_ERROR",
            utterance="Let me put you through to someone who can help you with this.",
        )

    raw = (result or "").strip().lower()
    is_match = raw == "match"

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
