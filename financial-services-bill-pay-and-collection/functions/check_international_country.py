"""Check whether a country is supported for app-based international payments.

This is a simplified example list. In production, replace ALLOWED_COUNTRIES
with the full set from your payments provider.
"""

from _gen import *  # <AUTO GENERATED>

# Example subset -- extend with your full supported-country list
ALLOWED_COUNTRIES = [
    "France",
    "Germany",
    "Ireland",
    "Italy",
    "Netherlands",
    "Spain",
    "United Kingdom",
    "United States of America",
]

# Common alternative names
COUNTRY_ALIASES = {
    "usa": "United States of America",
    "united states": "United States of America",
    "us": "United States of America",
    "uk": "United Kingdom",
    "holland": "Netherlands",
}


@func_description(
    "Check if a country is allowed for international payments through the app."
)
@func_parameter("country", "The destination country name mentioned by the user.")
@func_parameter("account_type", 'The account type: "PERSONAL" or "BUSINESS".')
def check_international_country(conv: Conversation, country: str, account_type: str):
    if not country:
        return "Please ask the user which country they would like to send to."

    country_lower = country.strip().lower()
    normalized = COUNTRY_ALIASES.get(country_lower, country)

    is_allowed = any(c.lower() == normalized.lower() for c in ALLOWED_COUNTRIES)

    if is_allowed:
        conv.say(
            "Great. Just log into the app, go to 'Pay & Transfer' and select "
            "'International Payment'. Then, submit the required details to "
            "process your payment."
        )
    else:
        return 'Call {{fn:handoff}} with reason="INTERNATIONAL_PAYMENTS"'
