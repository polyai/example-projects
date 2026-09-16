from _gen import *  # <AUTO GENERATED>
import plog
from functions.handoff import handoff
from functions.match_spelled_name_to_account import (
    account_name_parts,
    deterministic_name_match,
    handle_name_matched,
)


def _llm_name_prompt(
    conv: Conversation, account_name: str, user_stated_name: str
) -> str:
    candidates = getattr(conv.state, "idnv_candidate_patients", None) or []
    prompt = (
        "You are a detail-oriented name matcher for identity verification. "
        "Decide whether the name the user stated refers to the same person "
        "as the name on the account.\n\n"
    )
    if len(candidates) <= 1:
        prompt += (
            "IMPORTANT CONTEXT: The caller's phone number and date of birth "
            "have ALREADY been verified and uniquely match this account. "
            "This means identity is strongly established. Be generous with "
            "name matching, a match on first name OR last name alone is "
            "sufficient. Only return no_match if the stated name is clearly "
            "a completely different person (both first AND last name wrong).\n\n"
        )
    return prompt + (
        "The user's input was captured by voice (ASR), so it may contain "
        "transcription errors, nicknames, middle names, or different ordering "
        '(e.g. "Last, First"). Be reasonable and not overly strict: if it is '
        "clear they are referring to the same person, count it as a match.\n\n"
        f"Consult the transcript alternatives ({conv.transcript_alternatives}) "
        "to see if any of the transcript alternatives match the name on the account. "
        "(e.g., 'Jon', 'John', 'On' would match to 'John'.)\n"
        "Match criteria:\n"
        "1. Same person: Treat as match if first and last name clearly refer "
        'to the same person (e.g. "John Smith" vs "Jonathan Smith", '
        '"Smith John" vs "John Smith", "Mary Jane Doe" vs "Mary Doe"). '
        "Ignore middle names or extra words if first/last are consistent.\n"
        '2. ASR noise: Allow common ASR mistakes (e.g. "Jon" vs "John", '
        '"Stevens" vs "Stephens", homophones). Do not reject on minor '
        "spelling differences that could be voice transcription. Gendered "
        "variants of the same root name are likely ASR errors (e.g. "
        '"Patricia" vs "Patrick", "Andrea" vs "Andrew", "Alexandra" vs '
        '"Alexander"), treat these as a match.\n'
        "3. Do not match: Only return no_match if the names clearly refer to "
        "different people (different first and last name, or obviously wrong "
        "person).\n\n"
        f"Account name on file:\n{account_name!r}\n\n"
        f"User stated (from voice):\n{user_stated_name!r}\n\n"
        f"Transcript alternatives (from voice): \n{conv.transcript_alternatives}\n\n"
        "OUTPUT FORMAT:\n"
        "- If the names refer to the same person, return exactly: match\n"
        "- If they do not refer to the same person, return exactly: no_match\n\n"
        "You must return **ONLY** one of these two words. No other text."
    )


@func_latency_control(
    delay_before_responses_start=0,
    silence_after_each_response=3,
    delay_responses=[("Just looking that up now.", 2), ("One moment.", 3)],
)
def match_name_to_account(conv: Conversation, flow: Flow):
    log_prefix = "[match_name_to_account]: "
    patient = getattr(conv.state, "identified_patient", None)
    plog.info(f"{log_prefix} has_identified_patient={bool(patient)}")
    if not patient:
        conv.log.warning("match_name_to_account called but no identified_patient")
        return handoff(
            conv,
            reason="IDNV_NAME_MATCH_NO_ACCOUNT",
            utterance="Please hold while I transfer you to someone who can help.",
        )

    name_entity = conv.entities.full_name.value if conv.entities.full_name else None
    user_stated_name = str(name_entity or "").strip()
    if not user_stated_name:
        conv.log.warning("match_name_to_account called but no full_name entity")
        return handoff(
            conv,
            reason="IDNV_NAME_NOT_PROVIDED",
            utterance="Please hold while I transfer you to someone who can help.",
        )

    first, last = account_name_parts(patient)
    account_name = f"{first} {last}".strip() or "Unknown"
    conv.log.info(
        f"Transcript alternatives = {conv.transcript_alternatives}", is_pii=True
    )

    candidates = getattr(conv.state, "idnv_candidate_patients", None) or []
    is_match = deterministic_name_match(
        f"{user_stated_name} {conv.transcript_alternatives}",
        first,
        last,
        require_both=len(candidates) > 1,
    )
    llm_response = ""

    if not is_match:
        result = None
        try:
            result = conv.utils.prompt_llm(
                _llm_name_prompt(conv, account_name, user_stated_name),
                show_history=True,
            )
        except Exception as e:
            conv.log.warning(
                "match_name_to_account: prompt_llm failed, using deterministic fallback",
                error=str(e),
            )
        llm_response = str(result or "").strip()
        is_match = llm_response.lower() == "match"

    conv.log.info(
        "IDNV name match result",
        user_stated=user_stated_name,
        account_name=account_name,
        is_match=is_match,
        llm_response=llm_response[:50],
        is_pii=True,
    )

    if is_match:
        return handle_name_matched(conv, log_prefix)

    conv.write_metric("IDNV_NAME_SPELLING_ATTEMPTED", True)
    flow.goto_step(
        "Collect Spelled Name", "spoken name did not match; asking caller to spell"
    )
    return {
        "utterance": "I wasn't able to match that name to the account. Could you spell your first and last name for me?",
    }
