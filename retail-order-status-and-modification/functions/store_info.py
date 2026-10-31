"""Store facts in code: read from the variant attributes, never hardcoded.

Every caller-facing fact about the store (links, policies, pickup, hours) is a
variant attribute in config/variant_attributes.yaml, so onboarding can fill it
and a chain can give each site its own. Rules and topics read them with
{{attr:...}}; Python reads them through attr().

The sentences below are agent wording about an order's state, not store
policy, so they stay in code.
"""

from _gen import *  # <AUTO GENERATED>

# Links the agent can text: sms_id -> (variant attribute holding the URL, message body).
LINKS = {
    "website": ("website_url", "Shop online at {url}."),
    "returns_portal": ("returns_url", "Start or track a return or exchange at {url}."),
    "store_locator": ("store_locator_url", "Find a store at {url}."),
    "promotions": (
        "promotions_url",
        "See our current offers and discount codes at {url}.",
    ),
}

CANCELLED_OUT_OF_STOCK = (
    "We occasionally find an item is out of stock while fulfilling an order; any pending charge "
    "for it drops off the card within 5 to 7 business days, so they won't be charged."
)
CANCELLED_BY_CALLER = (
    "They'll get a confirmation email shortly, and any pending charge drops off their card within "
    "5 to 7 business days."
)
PROCESSING_SHIP = "We'll email a tracking link as soon as it ships."
PROCESSING_PICKUP = "We'll email as soon as it's ready to pick up in store."


@func_description(
    "[UTIL] Store facts from the variant attributes, not callable directly"
)
def store_info(conv: Conversation):
    return "Store facts module."


def attr(conv, name: str) -> str:
    """A variant attribute's value, or '' if the variant doesn't set it."""
    value = getattr(conv.variant, name, "") if conv.variant else ""
    return str(value or "").strip()


def sms_body(conv, sms_id: str) -> str:
    """The text for a store link, or '' if the variant has no URL for it."""
    attribute, text = LINKS[sms_id]
    url = attr(conv, attribute)
    return text.format(url=url) if url else ""
