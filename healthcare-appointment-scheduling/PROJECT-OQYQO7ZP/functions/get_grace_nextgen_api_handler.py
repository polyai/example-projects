from _gen import *  # <AUTO GENERATED>

from .api_handler import (  # noqa: F401
    NextGenApiError,
    NextGenApiHandler,  # noqa: F401
    NextGenDuplicatePersonError,
    NextGenHttpError,
    get_api_handler,
)


@func_description("Get the EHR API handler")
def get_grace_nextgen_api_handler(conv: Conversation):
    return get_api_handler(conv)
