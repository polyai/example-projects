"""Vulnerable customer detection utilities.

Provides keyword-based and ANI-based checks for identifying potentially
vulnerable callers who should be routed to a specialist team.
"""

import re

from _gen import *  # <AUTO GENERATED>
from functions.vc_keywords import VC_KEYWORDS


def get_vc_keyword_match(text: str) -> str | None:
    """Return the first VC keyword found in *text* (word-boundary match), or None."""
    if not text or not text.strip():
        return None
    pattern = r"\b(" + "|".join(re.escape(k) for k in VC_KEYWORDS) + r")\b"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    return match.group(1).lower() if match else None


def is_vulnerable_customer(conv: Conversation) -> bool:
    """Check whether the caller is flagged as a vulnerable customer.

    In production, this would query an external database (e.g. DynamoDB) by ANI.
    The template uses the mock API fallback so no real infrastructure is needed.
    """
    caller_number = conv.caller_number
    flags = conv.real_time_config.get("flags", {})
    if not flags:
        return False

    vc_handoff_enabled = flags.get("vc_handoff_enabled", False)
    if not vc_handoff_enabled or not caller_number:
        return False

    # Mock implementation -- replace with a real lookup in production
    try:
        from functions.mock_api import MockVulnerableCustomerCheck

        return MockVulnerableCustomerCheck.is_vulnerable(caller_number)
    except (ImportError, AttributeError):
        conv.log.warning("Mock VC check unavailable")
        return False


@func_description("[UTIL] Vulnerable customer detection utilities")
def handoff_utils(conv: Conversation):
    pass
