from _gen import *  # <AUTO GENERATED>


@func_description("[UTIL] Restaurant API factory. Do not call directly.")
def opentable_api(conv: Conversation):
    pass


def get_restaurant_api(conv):
    """Factory: return the mock restaurant API."""
    from functions.mock_api import MockOpenTableApi

    return MockOpenTableApi(conv)
