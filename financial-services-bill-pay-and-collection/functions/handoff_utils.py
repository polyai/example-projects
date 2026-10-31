"""Vulnerable customer detection utilities.

Provides keyword-based and ANI-based checks for identifying potentially
vulnerable callers who should be routed to a specialist team.
"""

from _gen import *  # <AUTO GENERATED>
import re
from typing import Optional

from functions.vc_keywords import VC_KEYWORDS


def get_vc_keyword_match(text: str) -> Optional[str]:
    """Return the first VC keyword found in *text* (word-boundary match), or None."""
    if not text or not text.strip():
        return None
    pattern = r"\b(" + "|".join(re.escape(k) for k in VC_KEYWORDS) + r")\b"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    return match.group(1).lower() if match else None


def is_vulnerable_customer(conv: Conversation) -> bool:
    """Whether the caller ID is flagged as a vulnerable customer.

    Only checked when real-time config flags.vc_handoff_enabled is true. The lookup
    goes through functions/api_client.py (mocked outside live).
    """
    flags = (conv.real_time_config or {}).get("flags", {}) or {}
    if not flags.get("vc_handoff_enabled") or not conv.caller_number:
        return False
    try:
        import functions.api_client as api_client

        return api_client.is_vulnerable_caller(conv, str(conv.caller_number))
    except Exception as e:
        conv.log.warning("Vulnerable customer check failed", error=str(e))
        return False


@func_description("[UTIL] Vulnerable customer detection utilities")
def handoff_utils(conv: Conversation):
    pass
