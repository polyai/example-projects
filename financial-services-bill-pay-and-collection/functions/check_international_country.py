from _gen import *  # <AUTO GENERATED>

# Countries allowed on the app for international payments
ALLOWED_COUNTRIES = [
    "Åland Islands",
    "Austria",
    "Azores",
    "Belgium",
    "Bulgaria",
    "Canary Islands",
    "Croatia",
    "Cyprus",
    "Czech Republic",
    "Denmark",
    "Estonia",
    "Finland",
    "France",
    "French Guiana",
    "Germany",
    "Gibraltar",
    "Greece",
    "Guadeloupe",
    "Guernsey",
    "Hungary",
    "Iceland",
    "Ireland",
    "Isle of Man",
    "Italy",
    "Jersey",
    "Latvia",
    "Liechtenstein",
    "Lithuania",
    "Luxembourg",
    "Madeira",
    "Malta",
    "Martinique",
    "Mayotte",
    "Monaco",
    "Netherlands",
    "Norway",
    "Poland",
    "Portugal",
    "Réunion",
    "Romania",
    "Saint Barthélemy",
    "Saint Martin",
    "Saint Pierre and Miquelon",
    "San Marino",
    "Slovakia",
    "Slovenia",
    "Spain",
    "Sweden",
    "Switzerland",
    "United States of America",
    "United Kingdom",
    "North Macedonia",
    "Albania",
    "Moldova",
    "Montenegro",
]

# Alternative names/mappings for countries (case-insensitive matching)
COUNTRY_ALIASES = {
    "usa": "United States of America",
    "united states": "United States of America",
    "us": "United States of America",
    "uk": "United Kingdom",
    "czechia": "Czech Republic",
    "holland": "Netherlands",
    "czech republic": "Czech Republic",
}

# APP_INSTRUCTION_PERSONAL = """
# # Country is allowed on app
# Say: "Great. Just log into the app, go to 'Pay & Transfer' and select 'International Payment'. Then, submit the required details to process your payment."
# """

# APP_INSTRUCTION_BUSINESS = """
# # Country is allowed on app
# Say: "Great. Just log into the app, go to 'Pay & Transfer' and select 'International Payment'. Then, submit the required details to process your payment."
# """

COUNTRY_NOT_ALLOWED = """
# Country is not allowed on app
Call {{fn:handoff}} with reason="INTERNATIONAL_PAYMENTS"
"""


@func_description(
    "Check if a country is allowed for international payments through the app. Returns appropriate routing based on whether the country is supported."
)
@func_parameter(
    "country",
    "The destination country name mentioned by the user. Extract the country name from their response.",
)
@func_parameter(
    "account_type",
    'The account type: "PERSONAL" or "BUSINESS". Determines which app instruction message to use if country is allowed.',
)
def check_international_country(conv: Conversation, country: str, account_type: str):
    """
    Check if the provided country is in the allowed list for app-based international payments.
    Returns appropriate YAML routing based on the result.
    """
    if not country:
        return "Please ask the user which country they would like to send to."

    country = country.strip()
    account_type = account_type.upper() if account_type else "PERSONAL"

    # Normalize country name for matching
    country_lower = country.lower()

    # Check aliases first
    normalized_country = COUNTRY_ALIASES.get(country_lower, country)

    # Check if country is in allowed list (case-insensitive)
    is_allowed = False
    # matched_country = None

    for allowed_country in ALLOWED_COUNTRIES:
        if (
            allowed_country.lower() == country_lower
            or allowed_country.lower() == normalized_country.lower()
        ):
            is_allowed = True
            # matched_country = allowed_country
            break

    # If not found, try fuzzy matching with LLM
    if not is_allowed:
        PROMPT = f"""
        # TASK
        The user mentioned the country: "{country}"

        Check if this country matches any of the following allowed countries (considering variations, abbreviations, and common names):
        {", ".join(ALLOWED_COUNTRIES)}

        Also consider these aliases:
        - USA/US/United States → United States of America
        - UK → United Kingdom
        - Czechia → Czech Republic
        - Holland → Netherlands

        Return JSON with:
        {{
            "is_allowed": true/false,
            "matched_country": "exact country name from the list if matched, or null"
        }}
        """

        result = conv.utils.prompt_llm(prompt=PROMPT, return_json=True, show_history=True)

        if result:
            is_allowed = result.get("is_allowed", False)
            # matched_country = result.get("matched_country")

    if is_allowed:
        # Country is allowed - return appropriate app instruction based on account type
        # if account_type == "BUSINESS":
        conv.say(
            "Great. Just log into the app, go to 'Pay & Transfer' and select 'International Payment'. Then, submit the required details to process your payment."
        )
        # else:
        #     return APP_INSTRUCTION_PERSONAL
    # return APP_INSTRUCTION_BUSINESS
    else:
        # Country is not allowed - route to handoff
        return COUNTRY_NOT_ALLOWED
