import datetime as dt
from zoneinfo import ZoneInfo

from _gen import *  # <AUTO GENERATED>

name_suffixes_to_remove = [
    "jr.",
    "sr.",
    "jr",
    "sr",
    "iii",
    "ii",
    "iv",
    "v",
    "esq",
    "md",
    "dr",
]


def levdistance(input_string: str, string_to_match: str) -> int:
    """
    Calculate the Levenshtein distance between two strings using dynamic programming.

    The Levenshtein distance is the minimum number of single-character edits
    (insertions, deletions, or substitutions) required to change one string into another.

    Args:
        input_string: The first string to compare
        string_to_match: The second string to compare

    Returns:
        int: The minimum edit distance between the two strings
    """

    rows = len(input_string) + 1
    cols = len(string_to_match) + 1
    dist = [[0 for x in range(cols)] for x in range(rows)]

    # source prefixes can be transformed into empty strings by deletions
    for i in range(1, rows):
        dist[i][0] = i

    # target prefixes can be created from an empty source string by inserting the characters
    for i in range(1, cols):
        dist[0][i] = i

    for col in range(1, cols):
        for row in range(1, rows):
            if input_string[row - 1] == string_to_match[col - 1]:
                cost = 0
            else:
                cost = 1
            dist[row][col] = min(
                dist[row - 1][col] + 1,  # deletion
                dist[row][col - 1] + 1,  # insertion
                dist[row - 1][col - 1] + cost,  # substitution
            )

    return dist[rows - 1][cols - 1]


def fuzzy_match(input_string: str, string_to_match: str) -> float:
    """
    Calculate fuzzy match percentage between two strings.

    This function normalizes strings by removing common name suffixes and whitespace,
    then calculates similarity based on Levenshtein distance. Higher percentages
    indicate more similar strings.

    Args:
        input_string: The first string to compare
        string_to_match: The second string to compare

    Returns:
        float: Similarity percentage (0.0 to 100.0), where 100.0 means identical strings
    """
    # Remove suffixes from both strings
    for suffix in name_suffixes_to_remove:
        if input_string.lower().endswith(suffix.lower()):
            input_string = input_string[: -len(suffix)]
        if string_to_match.lower().endswith(suffix.lower()):
            string_to_match = string_to_match[: -len(suffix)]

    # Remove trailing spaces
    input_string = input_string.strip()
    string_to_match = string_to_match.strip()

    distance = levdistance(input_string.lower(), string_to_match.lower())
    max_len = max(len(input_string), len(string_to_match))

    if max_len == 0:
        return 100.0

    ratio = 1 - distance / max_len
    return 100 * ratio


def verify_value(
    collected_value: str,
    reference_values: str | list[str],
    fuzzy_match_threshold: int,
) -> tuple[bool, str | None]:
    """
    Check if collected value matches any reference value using fuzzy matching.

    Args:
        collected_value: The value to verify
        reference_values: Single reference value or list of reference values
        fuzzy_match_threshold: Minimum similarity score (0-100) for a match

    Returns:
        Tuple of (is_match, matched_reference_value_or_None)
    """

    # Ensure reference values are a list
    if isinstance(reference_values, str):
        reference_values = [reference_values]

    # Check if the collected value matches any reference value
    for reference_value in reference_values:
        if (
            fuzzy_match(str(collected_value), str(reference_value))
            >= fuzzy_match_threshold
        ):
            return True, reference_value

    return False, None


def set_datetime(conv: Conversation, use_variants: bool = False, timezone: str = ""):
    """
    Set the datetime attributes on the conversation state.

    Args:
        conv: Conversation object containing state and optional variant info.
        use_variants (bool): Whether to use timezone from conv.variant.
        timezone (str): Timezone string to use if not using variants.

    Raises:
        ValueError: If use_variants is False and no timezone is provided.
    """
    if use_variants:
        tz = conv.variant.timezone
    else:
        if not timezone:
            raise ValueError("Timezone must be provided if use_variants is False.")
        tz = timezone

    now = dt.datetime.now(ZoneInfo(tz))
    conv.state.now = now
    conv.state.current_date = now.strftime("%A %d-%m-%Y")
    conv.state.current_weekday = now.strftime("%A")
    conv.state.current_time = now.strftime("%H:%M")
    conv.state.formatted_date_time = now.strftime("%A, %B %d, %Y at %I:%M %p")


def _get_counter_name(conv, flow) -> str:
    """
    Generate unique counter name for conversation/flow/step combination.

    Creates a hierarchical identifier that uniquely identifies a specific step
    within a conversation flow for retry counting purposes.

    Args:
        conv: Conversation object containing current_flow information
        flow: Flow object containing current_step information

    Returns:
        str: Unique counter name in format "flow_name/step_name"
    """
    return f"{conv.current_flow}/{flow.current_step}"


def get_retry_counter(conv, flow) -> int:
    """
    Get current retry counter for the conversation step.

    Retrieves the number of times the current step has been retried.
    Initializes retry_counters dictionary if it doesn't exist or is invalid.

    Args:
        conv: Conversation object with state containing retry_counters
        flow: Flow object identifying the current step

    Returns:
        int: Current retry count for this step (0 if never retried)
    """
    if not isinstance(conv.state.retry_counters, dict):
        conv.state.retry_counters = {}
    counter_name = _get_counter_name(conv, flow)
    return conv.state.retry_counters.get(counter_name, 0)


def increment_retry_counter(conv, flow) -> int:
    """
    Increment and return retry counter for the conversation step.

    Increases the retry count for the current step by 1 and returns the new value.
    Initializes retry_counters dictionary if it doesn't exist or is invalid.

    Args:
        conv: Conversation object with state containing retry_counters
        flow: Flow object identifying the current step

    Returns:
        int: New retry count after incrementing
    """
    if not isinstance(conv.state.retry_counters, dict):
        conv.state.retry_counters = {}
    counter_name = _get_counter_name(conv, flow)
    counter = conv.state.retry_counters.get(counter_name, 0) + 1
    conv.state.retry_counters[counter_name] = counter
    return counter


@func_description("A collection of util functions used by the step generator")
def step_utils(conv: Conversation):
    """
    A collection of util functions for the step generator.

    This function serves as the main entry point for step utilities.
    All utility functions (fuzzy_match, verify_value, counter functions, etc.)
    are available in the same scope when this code is executed.

    Args:
        conv: Conversation object (currently unused but kept for interface consistency)
    """
