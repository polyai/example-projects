
from _gen import *  # <AUTO GENERATED>


def search_user(conv: Conversation, email: str):
    """Search for a Zendesk user by email."""
    mock = get_zendesk_api(conv)
    if mock:
        return mock.search_user(conv, email)
    # No real implementation -- add your ticketing integration here.
    conv.log.warning("zendesk_client: no backend configured for search_user")
    return {"count": 0, "results": []}


def search_user_phone(conv: Conversation, phone_number: str):
    """Search for a Zendesk user by phone number."""
    mock = get_zendesk_api(conv)
    if mock:
        return mock.search_user_phone(conv, phone_number)
    # No real implementation -- add your ticketing integration here.
    conv.log.warning("zendesk_client: no backend configured for search_user_phone")
    return {"count": 0, "results": []}


def create_ticket(conv: Conversation):
    """Create a support ticket."""
    mock = get_zendesk_api(conv)
    if mock:
        return mock.create_ticket(conv)
    # No real implementation -- add your ticketing integration here.
    conv.log.warning("zendesk_client: no backend configured for create_ticket")
    return None


def update_ticket(
    conv: Conversation,
    ticket_id: str,
    ticket_status: str,
    comment: dict[str, str],
    **properties,
):
    """Update a support ticket."""
    mock = get_zendesk_api(conv)
    if mock:
        return mock.update_ticket(conv, ticket_id, ticket_status, comment, **properties)
    # No real implementation -- add your ticketing integration here.
    conv.log.warning("zendesk_client: no backend configured for update_ticket")
    return None


def init_zendesk_client(conv: Conversation):
    """Initialize the ticketing client. Call this in start_function."""
    mock = get_zendesk_api(conv)
    if mock:
        return mock.init_zendesk_client(conv)
    # No real implementation -- add your ticketing integration here.
    conv.log.warning("zendesk_client: no backend configured for init_zendesk_client")


def update_custom_fields_on_ticket(
    conv: Conversation,
    first_name: str | None = None,
    last_name: str | None = None,
    loyalty_number: str | None = None,
    postal_code: str | None = None,
):
    """Update custom fields on a support ticket."""
    mock = get_zendesk_api(conv)
    if mock:
        return mock.update_custom_fields_on_ticket(
            conv, first_name, last_name, loyalty_number, postal_code
        )
    # No real implementation -- add your ticketing integration here.
    conv.log.warning(
        "zendesk_client: no backend configured for update_custom_fields_on_ticket"
    )
    return None


def get_zendesk_api(conv):
    """Return MockZendeskClient when USE_MOCK_API is set, otherwise None.

    To integrate a real ticketing system, return your client object here instead of None.
    """
    if getattr(conv.state, "USE_MOCK_API", False):
        from .mock_api import get_mock_zendesk

        return get_mock_zendesk()
    return None


@func_description("Client for Zendesk APIs")
def zendesk_client(conv: Conversation):
    pass
