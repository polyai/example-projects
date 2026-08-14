"""Extract the caller's date/time preference from conversation history via LLM."""

from _gen import *  # <AUTO GENERATED>
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Optional

import plog


@dataclass(frozen=True)
class TimePreferenceResult:
    """Structured date/time preference extracted from conversation."""

    has_preference: bool
    requested_date: Optional[
        str
    ]  # Resolved ISO date, weekday name, or relative like "next week"
    requested_time: Optional[
        str
    ]  # Normalized time string compatible with select_closest_slot


_LOG_PREFIX = "[extract_time_preference]: "


def extract_time_preference_from_conversation(
    conv: Conversation,
) -> TimePreferenceResult:
    """
    Use prompt_llm with full conversation history to detect any date/time preference
    the caller expressed. Returns the MOST RECENTLY expressed preference.

    The returned ``requested_date`` and ``requested_time`` are normalized to formats
    accepted by ``select_closest_slot`` in ``slot_matching.py``.
    """
    today_str = datetime.now(UTC).strftime("%Y-%m-%d")
    prompt = (
        "You are reviewing a voice conversation to extract the caller's appointment scheduling preference.\n\n"
        f"Today's date is {today_str}.\n\n"
        "Look at the conversation and determine if the caller expressed a preferred date, "
        "day of week, time of day, or time range for their new appointment. "
        "Use the MOST RECENTLY expressed preference if multiple are mentioned.\n\n"
        "Examples:\n"
        "- 'next friday' → resolve to ISO date, e.g. '2026-04-03'\n"
        "- 'tuesday afternoons' → date: 'tuesday', time: 'afternoon'\n"
        "- 'march 31st at 1pm' → date: '2026-03-31', time: 'at 13:00'\n"
        "- 'morning' or 'mornings' → date: null, time: 'morning'\n"
        "- 'tomorrow' → date: 'tomorrow', time: null\n"
        "- 'as soon as possible', 'whatever works', 'any time' → has_preference: false\n"
        "- (no preference stated at all) → has_preference: false\n\n"
        "Rules for the output:\n"
        "1. Resolve specific dates to ISO format YYYY-MM-DD when possible.\n"
        "2. For weekday-only references ('tuesdays', 'on a tuesday'), use the weekday name lowercase "
        "(e.g. 'tuesday').\n"
        "3. For time of day, use one of: 'morning', 'afternoon', 'evening', 'earlier', "
        "'at HH:MM' (24-hour), 'before HH:MM', 'after HH:MM'.\n"
        "4. If the user says 'earlier' or 'earliest', use time: 'earlier'.\n"
        "5. Return has_preference: false if no useful date/time constraint was expressed.\n"
        "6. IMPORTANT: Do NOT treat answers about hospitalization or discharge dates as scheduling "
        "preferences. For example, if the caller says 'I was discharged yesterday' or 'yesterday' "
        "in response to a discharge date question, that is NOT a preference for when to schedule "
        "their appointment. Only return has_preference: true when the caller explicitly states "
        "when they want their upcoming appointment.\n\n"
        "OUTPUT: Return ONLY a JSON object with no other text:\n"
        '{"has_preference": true/false, "requested_date": "..." or null, "requested_time": "..." or null}\n\n'
        'Example: {"has_preference": true, "requested_date": "tuesday", "requested_time": "afternoon"}'
    )

    try:
        result = conv.utils.prompt_llm(prompt, show_history=True)
        raw = (result or "").strip()
        plog.info(f"{_LOG_PREFIX} llm_raw='{raw[:150]}'", is_pii=True)

        # Strip markdown code fences if present
        if raw.startswith("```"):
            lines = raw.splitlines()
            inner = [line for line in lines[1:] if line.strip() != "```"]
            raw = "\n".join(inner).strip()

        parsed = json.loads(raw)
        has_pref = bool(parsed.get("has_preference", False))
        req_date: Optional[str] = parsed.get("requested_date") or None
        req_time: Optional[str] = parsed.get("requested_time") or None

        plog.info(
            f"{_LOG_PREFIX} has_preference={has_pref} "
            f"requested_date='{req_date}' requested_time='{req_time}'",
            is_pii=True,
        )
        return TimePreferenceResult(
            has_preference=has_pref,
            requested_date=req_date,
            requested_time=req_time,
        )

    except Exception as e:
        plog.info(f"{_LOG_PREFIX} failed to extract preference error='{e}'")
        conv.log.warning(
            "extract_time_preference: failed to parse LLM response", error=str(e)
        )
        return TimePreferenceResult(
            has_preference=False, requested_date=None, requested_time=None
        )


@func_description(
    "Extract the caller's appointment time preference from conversation history (utility module; not called directly by LLM)."
)
def extract_time_preference(conv: Conversation) -> None:
    """Platform entry point for this module (helpers are imported directly)."""
    log_prefix = "[extract_time_preference.extract_time_preference]: "
    plog.info(f"{log_prefix} invoked")
