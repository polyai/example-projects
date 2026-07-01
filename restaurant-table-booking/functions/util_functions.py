import re

from _gen import *  # <AUTO GENERATED>
from functions.guest_search import is_guest_search_enabled

DOUBLE = "DOUBLE"


def transform_name_spelling_string(name_spelling: str):
    """Pre-process a name spelling before using it in booking for example"""
    name_spelling = name_spelling.replace("-", "").replace(" ", "").upper()
    result = ""
    i = 0
    while i < len(name_spelling):
        # Check if we have "DOUBLE" and at least one character after it
        if i + len(DOUBLE) < len(name_spelling) and name_spelling[i : i + len(DOUBLE)] == DOUBLE:
            # Skip the substring "DOUBLE"
            i += len(DOUBLE)
            # Double the next character, if it exists
            if i < len(name_spelling):
                result += name_spelling[i] * 2
                i += 1
        else:
            result += name_spelling[i]
            i += 1

    return result


def validate_phone_number(conv, phone_number: str):
    """ """
    # Normalise: keep only + and digits so LLM formatting never leaks through
    if not phone_number.startswith("+"):
        phone_number = re.sub(r"\D", "", phone_number)
    else:
        phone_number = "+" + re.sub(r"\D", "", phone_number[1:])
    pattern = r"^\+(\d{1,3})\s*(\d{1,14})$"

    # If phone number doesn't start with +, prepend country code
    if not phone_number.startswith("+"):
        country_code = get_country_code_prefix(conv)
        phone_number = f"+{country_code} {phone_number}"
    elif phone_number.startswith("+353"):
        phone_number = f"+353 {phone_number[4:]}"
    elif phone_number.startswith("+44"):
        phone_number = f"+44 {phone_number[3:]}"
    elif phone_number.startswith("+61"):
        phone_number = f"+61 {phone_number[3:]}"
    elif phone_number.startswith("+1"):
        phone_number = f"+1 {phone_number[2:]}"

    if match := re.match(pattern, phone_number):
        country_code = int(match.group(1))
        phone_number_without_code = match.group(2).lstrip("0")
        # UK: national number should be 10 digits for mobile (7xxxxxxxxx); reject wrong length (e.g. 12 from extra 0)
        if country_code == 44 and len(phone_number_without_code) != 10:
            return "It seems like the phone number had too many or too few digits. There may have been an issue with the transcription. Check the number against what the user said, or ask them to repeat it slowly."
        return country_code, phone_number_without_code

    return "It seems like the phone number might be invalid. Ask the user for their number again."


def is_valid_potential_mobile_number(conv: Conversation, phone_number: str):
    """
    Validates if a phone number is a valid UK mobile phone number or a US phone number
    """

    MOBILE_NUMBER_PATTERNS = {
        "GB": r"^(\+447|07)\d{8,9}$",  # UK
        "IE": r"^(\+353|0)8[3-9]\d{7}$",  # Ireland
        "AU": r"^(\+61|0)4\d{8}$",  # Australia
        "US": r"^(\+1)?[2-9]\d{9}$",  # US (mobile indistinct from landline)
        "CA": r"^(\+1)?[2-9]\d{9}$",  # CA (mobile indistinct from landline)
    }
    if not phone_number:
        return False
    # Regular expression to match UK phone numbers starting with +447 and followed by 9 digits
    country_code = get_country_code(conv)
    pattern = MOBILE_NUMBER_PATTERNS.get(country_code)

    if not pattern:
        return False  # Unsupported country code

    return re.match(pattern, phone_number) is not None


def get_country_code_prefix(conv):
    if conv.variant.timezone == "Europe/London":
        country_code = "44"
    elif conv.variant.timezone.startswith("Australia"):
        country_code = "61"
    elif conv.variant.timezone.startswith("Europe/Dublin"):
        country_code = "353"
    elif (
        conv.variant.timezone.startswith("Canada") or conv.variant.timezone in canada_city_timezones
    ):
        country_code = "1"
    else:
        country_code = "1"  # US
    return country_code


def get_country_code(conv):
    if conv.variant.timezone == "Europe/London":
        country_code = "GB"
    elif conv.variant.timezone.startswith("Australia"):
        country_code = "AU"
    elif conv.variant.timezone.startswith("Europe/Dublin"):
        country_code = "IE"
    elif conv.variant.timezone.startswith(
        "Canada" or conv.variant.timezone in canada_city_timezones
    ):
        country_code = "CA"
    else:
        country_code = "US"
    return country_code


def name_to_spelling(name: str) -> str:
    """Convert a name to its spelled-out form (e.g., 'John' -> 'J, O, H, N')."""
    cleaned = re.sub(r"[^A-Za-z]", "", name)
    return ", ".join(cleaned.upper())


def is_na(conv, arg):
    """Check if a value represents a null/not-available value."""
    if arg is None:
        return True
    if isinstance(arg, (int, float)):
        return arg == -1
    if isinstance(arg, bool):
        return False
    if not isinstance(arg, str):
        return False
    if not arg:
        return True
    return arg.upper() in ["NA", "N/A", "UNKNOWN"] or arg == "-"


@func_description("Don't ever call this function. This is meant for importing function only.")
def util_functions(conv: Conversation):
    # Add your function definition here.
    # You can optionally return a string that will be fed back to the LLM.
    pass


canada_city_timezones = [
    "America/Atikokan",
    "America/Blanc-Sablon",
    "America/Cambridge_Bay",
    "America/Creston",
    "America/Dawson",
    "America/Dawson_Creek",
    "America/Edmonton",
    "America/Fort_Nelson",
    "America/Glace_Bay",
    "America/Goose_Bay",
    "America/Halifax",
    "America/Inuvik",
    "America/Iqaluit",
    "America/Moncton",
    "America/Nipigon",
    "America/Pangnirtung",
    "America/Rainy_River",
    "America/Rankin_Inlet",
    "America/Regina",
    "America/Resolute",
    "America/St_Johns",
    "America/Swift_Current",
    "America/Thunder_Bay",
    "America/Toronto",
    "America/Vancouver",
    "America/Whitehorse",
    "America/Winnipeg",
    "America/Yellowknife",
]


def extract_name(
    conv: Conversation,
    transcript_alternatives: str,
    default_first_name: str = "UNKNOWN",
    default_last_name: str = "UNKNOWN",
) -> tuple[str, str, bool, bool]:
    """
    LLM-powered name extraction with transcript alternatives.

    Uses an LLM to extract first and last names from messy phone-call transcripts.
    Falls back to provided defaults if extraction fails or returns UNKNOWN.

    Args:
        conv: Conversation object for LLM access
        transcript_alternatives: ASR transcript alternatives to analyze
        default_first_name: Fallback if first name can't be extracted
        default_last_name: Fallback if last name can't be extracted

    Returns:
        Tuple of (first_name, last_name, known_first_name, known_last_name)
    """
    transcript_alternatives = str(transcript_alternatives)

    guest_hints_block = ""
    has_guest_hints = bool(
        is_guest_search_enabled(conv) and getattr(conv.state, "guest_search_name_hints", None)
    )
    if has_guest_hints:
        guest_hints_block = f"""

        ## GUEST DATABASE MATCH (HIGHEST PRIORITY)

        We looked up the caller's phone number in the restaurant's guest database and found:
        {conv.state.guest_search_name_hints}

        This is a verified guest record. The transcript names are from noisy ASR and are very
        likely garbled versions of the database name.

        Apply the database spelling when BOTH first AND last name from the transcript could be
        ASR errors of the same database entry (ASR adds/drops letters, swaps sounds, etc.).
        When only ONE of first/last name is phonetically close, keep BOTH transcript names
        as-is — someone else may be booking under that phone number.

        Examples (DB = "Niamh Ng"):
        - "Neeve Ang" → "Niamh Ng" (both are plausible ASR errors)
        - "Niamh Ang" → "Niamh Ng" (first matches, "Ang" is plausible ASR of "Ng")
        - "Niamh Smith" → keep "Niamh Smith" (first matches but "Smith" ≠ "Ng")
        - "Sarah Williams" → keep "Sarah Williams" (neither matches)
        """

    LLM_PROMPT = f"""
        ## TASK
        You are an expert value extractor. From messy phone-call transcripts (spoken + spelled),
        extract the user's *first name* and *last name*.


        # GUIDELINES

        Mistranscriptions are very likely, including random noise (e.g. redundant initial characters).
        Use both the spoken and spelled inputs. Take the whole conversation context into account.
        Reconcile phonetically similar variants. If you cannot extract a value, use "UNKNOWN".
        Give additional weight to any form that looks like a real, common name in any language.

        For the `known_first_name` and `known_last_name` outputs:
        - Return `true` if you recognize the value as a valid name in any language, culture, or
        widely used name list (given names and surnames).
        - Return `false` if you are uncertain or if the field is "UNKNOWN".

        {guest_hints_block}
        ## TRANSCRIPT ALTERNATIVES

        Apart from the conversation history, here are some ASR transcript alternatives for each turn.
        Use this information to extract the most likely first and last names.
        {transcript_alternatives}

        ## OUTPUT

        Return ONLY valid minified JSON with these EXACT keys:
        {{
        "first_name": "<string or 'UNKNOWN'>",
        "last_name": "<string or 'UNKNOWN'>",
        "known_first_name": <true|false>,
        "known_last_name": <true|false>
        }}
    """

    llm_out = (
        conv.functions.custom_llm_call(
            prompt=LLM_PROMPT,
            return_json=True,
        )
        or {}
    )

    llm_first_name = llm_out.get("first_name", "").strip()
    llm_last_name = llm_out.get("last_name", "").strip()

    def parse_bool_field(value) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() == "true"
        return False

    first_name = (
        llm_first_name if llm_first_name and llm_first_name != "UNKNOWN" else default_first_name
    )
    last_name = llm_last_name if llm_last_name and llm_last_name != "UNKNOWN" else default_last_name
    known_first_name = parse_bool_field(llm_out.get("known_first_name"))
    known_last_name = parse_bool_field(llm_out.get("known_last_name"))

    return first_name, last_name, known_first_name, known_last_name
