import plog
import requests
from _gen import *  # <AUTO GENERATED>
from functions.get_token import get_token

GUEST_SEARCH_BASE_URL = "https://platform.opentable.com/api/v1/guestsearch"
GUEST_SEARCH_TIMEOUT = 7
GUEST_SEARCH_DISABLED_VARIANTS = frozenset()


@func_description("[UTIL] Search OpenTable guest database by phone number. Do not call directly.")
def guest_search(conv: Conversation):
    pass


def _format_candidate_hints(candidates: list) -> str:
    """Format candidate names into a hint string for prompts."""
    if not candidates:
        return ""
    names = []
    for c in candidates[:5]:
        first = c.get("firstName", "")
        last = c.get("lastName", "")
        if first or last:
            names.append(f"{first} {last}".strip())
    if not names:
        return ""
    return "Possible guest names from database: " + ", ".join(names)


def is_guest_search_enabled(conv) -> bool:
    """Check if guest search is enabled for the current variant."""
    return conv.variant_name not in GUEST_SEARCH_DISABLED_VARIANTS


@plog.tmp_bind(api_integration="opentable")
def run_guest_search(conv, phone_number=None):
    """Call Guest Search API and store results in conv.state."""
    if not phone_number:
        conv.log.info("Guest search skipped - no phone number available")
        return

    rid = conv.variant.rid
    if not rid or not rid.strip().isdigit():
        conv.log.info("Guest search skipped - no valid RID", rid=rid)
        return

    url = f"{GUEST_SEARCH_BASE_URL}/restaurants/{rid}/guests/structuredSearch"
    token = get_token(conv)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    body = {"phone": phone_number}

    try:
        res = requests.post(url, json=body, headers=headers, timeout=GUEST_SEARCH_TIMEOUT)
        conv.log.info(
            "Guest search API response",
            status_code=res.status_code,
            url=url,
            phone=phone_number,
            response=res.text,
            is_pii=True,
        )

        if not res.ok:
            conv.log.error(
                "Guest search API error",
                status_code=res.status_code,
                response=res.text,
            )
            return

        data = res.json()
        count = data.get("count", 0)
        candidates = data.get("candidates", [])
        primary = data.get("primaryGuest")

        conv.state.guest_search_candidates = candidates
        conv.state.guest_search_primary = primary
        conv.state.guest_search_name_hints = _format_candidate_hints(candidates)

        if conv.state.guest_search_name_hints:
            conv.write_metric("GUEST_SEARCH_RESULTS_FOUND", write_once=True)

        conv.log.info(
            "Guest search completed",
            count=count,
            has_primary=primary is not None,
            hints=conv.state.guest_search_name_hints,
            is_pii=True,
        )

    except requests.exceptions.Timeout:
        conv.log.error("Guest search API timeout")
    except Exception as e:
        conv.log.error("Guest search API exception", error=e)
