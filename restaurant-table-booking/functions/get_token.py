import plog
import requests
from _gen import *  # <AUTO GENERATED>
from requests.auth import HTTPBasicAuth


@func_description("Gets the bearer token")
def get_token(conv: Conversation):
    try:
        auth_url = "https://oauth.opentable.com/api/v2/oauth/token?grant_type=client_credentials"
        secret = conv.utils.get_secret("opentable_api")
        basic = HTTPBasicAuth(secret["username"], secret["password"])
        response = requests.request("GET", auth_url, auth=basic, timeout=7)
        return response.json()["access_token"]
    except Exception as e:
        plog.error("Could not get token", error=e)
        raise e
