"""Defaults and helpers for handoff / deflection settings from conv.real_time_config['handoff_controls'].

Constants match client-facing names: invalid post-FAQ (handoff without valid soft path after FAQ); OOS pre-FAQ (no
FAQ yet); OOS post-FAQ (after FAQ, banking but unhandled). See docs/sandbox_config.md.
"""

from typing import Any, Optional

from _gen import *  # <AUTO GENERATED>

DEFAULT_INVALID_HANDOFF_POST_FAQ_DEFLECTIONS = 1
DEFAULT_OOS_PRE_FAQ_DEFLECTIONS = 1
DEFAULT_OOS_POST_FAQ_DEFLECTIONS = 2
DEFAULT_SPEAK_TO_NO_INTENT_DEFLECTIONS = 4


def _as_non_negative_int(value: Any, default: int) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    if n < 0:
        return 0
    return min(n, 50)


def get_handoff_controls_raw(conv) -> dict[str, Any]:
    raw = conv.real_time_config.get("handoff_controls")
    return raw if isinstance(raw, dict) else {}


def get_invalid_handoff_post_faq_deflections(conv) -> int:
    limits = get_handoff_controls_raw(conv).get("deflection_limits")
    if not isinstance(limits, dict):
        return DEFAULT_INVALID_HANDOFF_POST_FAQ_DEFLECTIONS
    return _as_non_negative_int(
        limits.get("invalid_handoff_post_faq_deflections"),
        DEFAULT_INVALID_HANDOFF_POST_FAQ_DEFLECTIONS,
    )


def get_out_of_scope_pre_faq_deflections(conv) -> int:
    limits = get_handoff_controls_raw(conv).get("deflection_limits")
    if not isinstance(limits, dict):
        return DEFAULT_OOS_PRE_FAQ_DEFLECTIONS
    return _as_non_negative_int(
        limits.get("out_of_scope_pre_faq_deflections"),
        DEFAULT_OOS_PRE_FAQ_DEFLECTIONS,
    )


def get_out_of_scope_post_faq_deflections(conv) -> int:
    limits = get_handoff_controls_raw(conv).get("deflection_limits")
    if not isinstance(limits, dict):
        return DEFAULT_OOS_POST_FAQ_DEFLECTIONS
    return _as_non_negative_int(
        limits.get("out_of_scope_post_faq_deflections"),
        DEFAULT_OOS_POST_FAQ_DEFLECTIONS,
    )


def get_speak_to_no_intent_deflections(conv) -> int:
    """
    Deflections for SPEAK_TO/N/A when no QA exists yet.
    Hard-capped at 4 to stay within the built-in utterance set.
    """
    limits = get_handoff_controls_raw(conv).get("deflection_limits")
    if not isinstance(limits, dict):
        return DEFAULT_SPEAK_TO_NO_INTENT_DEFLECTIONS
    configured = _as_non_negative_int(
        limits.get("speak_to_no_intent_deflections"),
        DEFAULT_SPEAK_TO_NO_INTENT_DEFLECTIONS,
    )
    return min(configured, 4)


def get_rtc_handoff_category_for_reason(conv, reason: str) -> Optional[str]:
    """Return 'valid', 'soft', 'invalid', or None if not listed in RTC (caller uses code default)."""
    rows = get_handoff_controls_raw(conv).get("handoff_reasons")
    if not isinstance(rows, list):
        return None
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("handoff_reason") != reason:
            continue
        cat = row.get("category")
        if isinstance(cat, str):
            cat = cat.strip().lower()
        if cat == "disabled":
            cat = "invalid"
        if cat in ("valid", "soft", "invalid"):
            return cat
    return None


def get_rtc_necessary_handoff_policy(conv, reason: str) -> Optional[str]:
    """For necessary handoff reasons: ``soft``, ``invalid``, or None (direct transfer unless RTC says otherwise)."""
    cat = get_rtc_handoff_category_for_reason(conv, reason)
    if cat in ("soft", "invalid"):
        return cat
    return None


def get_rtc_offered_handoff_policy(
    conv, reason: str, valid_offered_reasons: set[str]
) -> Optional[str]:
    """
    For FAQ offered handoff reasons, return policy from RTC:
    - "valid": allow direct handoff
    - "soft": require prior check_agent_availability offer
    - "invalid": neither offer nor transfer (post-FAQ invalid deflection)
    - None: reason is not configured in RTC (treat as invalid for offered-hand-off path)
    """
    if reason not in valid_offered_reasons:
        return None
    return get_rtc_handoff_category_for_reason(conv, reason)


# Backwards-compatibility alias: some runtimes may still import the old name.
def requires_soft_handoff_offer_before_transfer(
    conv, reason: str, valid_offered_reasons: set[str]
) -> bool:
    """True when transfer is not RTC ``valid`` (includes ``soft``, missing RTC row, and not in valid_offered set)."""
    policy = get_rtc_offered_handoff_policy(conv, reason, valid_offered_reasons)
    return policy != "valid"


@func_description(
    "[UTIL] DO NOT CALL DIRECTLY Defaults and helpers for handoff / deflection settings"
)
def real_time_handoff_config(conv: Conversation):
    # Add your function definition here.
    # You can optionally return a string that will be fed back to the LLM.
    pass
