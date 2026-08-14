
from _gen import *  # <AUTO GENERATED>


def get_email_by_phone(
    conv,
    phone_number: str,
    *,
    country_code: str | None = None,
    timeout: int | None = None,
) -> str | None:
    """Look up a customer's email by phone number.

    Delegates to the mock/real backend returned by get_customer_api().
    Replace get_customer_api() with your CRM integration.
    """
    api = get_customer_api(conv)
    if api:
        return api.get_email_by_phone(conv, phone_number, timeout=timeout)
    # No real implementation -- add your customer API integration here.
    conv.log.warning("customer_core_api: no backend configured for get_email_by_phone")
    return None


def get_customer_api(conv):
    """Return MockCustomerCoreApi when USE_MOCK_API is set, otherwise None.

    To integrate a real customer API, return your client object here instead of None.
    """
    if getattr(conv.state, "USE_MOCK_API", False):
        from .mock_api import get_mock_customer

        return get_mock_customer()
    return None


@func_description("Customer Core API client")
def customer_core_api(conv: Conversation):
    pass
