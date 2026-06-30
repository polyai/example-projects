from _gen import *  # <AUTO GENERATED>
from flows.idnv.function_steps.match_name_to_account import (
    _account_display_name,
    _handle_name_matched,
)
from functions.handoff import handoff


def match_spelled_name_to_account(conv: Conversation, flow: Flow):
    """Match a spelled name against the account after the spoken name failed."""
    log_prefix = "[match_spelled_name_to_account]: "
    patient = getattr(conv.state, "identified_patient", None)
    if not patient:
        return handoff(
            conv,
            reason="IDNV_NAME_MATCH_NO_ACCOUNT",
            utterance="Please hold while I transfer you to someone who can help.",
        )

    account_name = _account_display_name(patient)

    prompt = (
        "You are a name matcher for identity verification. The caller's FIRST "
        "spoken name did not match, so they were asked to spell or repeat their "
        "name. You must now evaluate ONLY the caller's SECOND attempt — the "
        "response given AFTER the agent asked them to spell their name.\n\n"
        "IMPORTANT: Completely IGNORE the first name the caller gave earlier in "
        "the conversation. It was wrong or misheard. Only use the caller's most "
        "recent response (after the spelling request) to determine the name.\n\n"
        "The caller may have:\n"
        "- Spelled letters out loud (e.g. 'J-O-H-N' or 'Jay, Ay, Ess, Oh, En')\n"
        "- Said the name normally instead of spelling it\n"
        "- Given a mix of spelling and speaking\n\n"
        "ASR often transcribes individual letters as words or similar-sounding "
        "words. Reconstruct the intended name generously.\n\n"
        "Match criteria (be lenient — this is a second chance):\n"
        "1. If the reconstructed first AND last name are clearly the same person "
        "as the account, return match.\n"
        "2. Allow ASR errors in individual letters (e.g. 'B'/'D', 'M'/'N', "
        "'S'/'F'), homophones ('Down'/'Dunn'), nicknames ('Jon'/'John', "
        "'Mike'/'Michael'), and minor spelling differences.\n"
        "3. Only return no_match if the names clearly refer to a different "
        "person.\n\n"
        f"Account name on file:\n{account_name!r}\n\n"
        f"Transcript alternatives (from ASR): \n{conv.transcript_alternatives}\n\n"
        "OUTPUT FORMAT:\n"
        "Return ONLY one word: match or no_match"
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
    conv.log.info(
        "IDNV spelled name match result",
        account_name=account_name,
        is_match=is_match,
        llm_response=(result or "").strip()[:50],
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

    return _handle_name_matched(conv, log_prefix)
