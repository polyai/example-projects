from _gen import *  # <AUTO GENERATED>
from functions.opentable_api import get_restaurant_api

GUEST_SEARCH_DISABLED_VARIANTS = frozenset()


@func_description("[UTIL] Search guest database by phone number. Do not call directly.")
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


def run_guest_search(conv, phone_number=None):
    """Call Guest Search API (via mock) and store results in conv.state."""
    if not phone_number:
        conv.log.info("Guest search skipped - no phone number available")
        return

    api = get_restaurant_api(conv)
    try:
        data = api.guest_search(phone_number)
        candidates = data.get("candidates", [])
        primary = data.get("primaryGuest")

        conv.state.guest_search_candidates = candidates
        conv.state.guest_search_primary = primary
        conv.state.guest_search_name_hints = _format_candidate_hints(candidates)

        if conv.state.guest_search_name_hints:
            conv.write_metric("GUEST_SEARCH_RESULTS_FOUND", write_once=True)

        conv.log.info(
            "Guest search completed",
            count=data.get("count", 0),
            has_primary=primary is not None,
            hints=conv.state.guest_search_name_hints,
            is_pii=True,
        )

    except Exception as e:
        conv.log.error("Guest search exception", error=e)
