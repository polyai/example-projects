"""
API handler factory for the healthcare template.

Returns MockApiHandler by default — no credentials or external services needed.
To integrate a real EHR system, replace MockApiHandler with your own implementation
that exposes the same interface (see mock_api.py for the method signatures).
"""

from _gen import *  # <AUTO GENERATED>

from .mock_api import MockApiHandler


class NextGenApiError(Exception):
    """Base exception for API errors."""


class NextGenDuplicatePersonError(NextGenApiError):
    """Raised when a duplicate person is detected."""

    def __init__(self, message: str, person_id: str | None = None):
        super().__init__(message)
        self.person_id = person_id


class NextGenHttpError(NextGenApiError):
    """Raised on HTTP-level errors from the EHR API."""

    def __init__(
        self, message: str, status_code: int | None = None, response_body: str = ""
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


def get_api_handler(conv):
    """Factory that returns the API handler. Always returns MockApiHandler in the template."""
    return MockApiHandler(conv)


get_grace_nextgen_api_handler = get_api_handler


@func_description("Get the EHR API handler")
def api_handler(conv: Conversation):
    return get_api_handler(conv)
