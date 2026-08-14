from _gen import *  # <AUTO GENERATED>
from functions.util_functions import (
    extract_name,
    get_country_code,
    is_na,
    is_valid_potential_mobile_number,
    name_to_spelling,
    transform_name_spelling_string,
)


@func_description('Save the name of the customer. Default unknown values to "N/A".')
@func_parameter(
    "first_name",
    'Default to "N/A" if not specified. The customer\'s first name. The input comes over the ASR channel so sanitise it before saving (e.g. add upper case).',
)
@func_parameter(
    "last_name",
    'Default to "N/A" if not specified. The customer\'s last name. The input comes over the ASR channel so sanitise it before saving (e.g. add upper case). If the user refuses to provide it, pass "-".',
)
def customer_name_given(
    conv: Conversation, flow: Flow, first_name: str, last_name: str
):
    def in_history(value: str) -> bool:
        if not isinstance(conv.state.get("values_in_history"), set):
            conv.state.values_in_history = set()
        if value in conv.state.values_in_history:
            return True
        conv.state.values_in_history.add(value)
        return False

    # --- Name Collection ---
    if is_na(conv, first_name) and is_na(conv, last_name):
        conv.write_metric("FIRST_NAME_REQUESTED", write_once=True)
        conv.write_metric("LAST_NAME_REQUESTED", write_once=True)
        return "Ask the user for their first and last name in a natural, conversational way."

    if not isinstance(conv.state.get("customer_name_alternatives"), list):
        conv.state.customer_name_alternatives = []
    if getattr(conv, "transcript_alternatives", None):
        conv.state.customer_name_alternatives += conv.transcript_alternatives

    if is_na(conv, first_name):
        conv.write_metric("FIRST_NAME_REQUESTED", write_once=True)
        return "Ask the user for their first name in a natural, conversational way."

    last_name_refused = last_name == "-"

    if not last_name_refused and is_na(conv, last_name):
        conv.write_metric("LAST_NAME_REQUESTED", write_once=True)
        return "Ask the user for their last name in a natural, conversational way."

    # --- 1) LLM extraction for both names ---
    if not in_history("customer_name_first_llm_extraction"):
        (
            conv.state.first_name,
            conv.state.last_name,
            conv.state.known_first_name,
            conv.state.known_last_name,
        ) = extract_name(
            conv,
            conv.state.customer_name_alternatives,
            default_first_name=first_name if not is_na(conv, first_name) else "UNKNOWN",
            default_last_name=last_name if not is_na(conv, last_name) else "UNKNOWN",
        )

    if last_name_refused:
        conv.log.info(
            "User refused to give their last name. Using their first name as last name.",
            first_name=conv.state.get("first_name", first_name),
        )
        conv.write_metric("CREATE_BOOKING_LAST_NAME_MISSING")
        if conv.state.get("first_name"):
            conv.state.last_name = conv.state.first_name
            conv.state.known_last_name = conv.state.known_first_name

    # --- 2) Confirm or ask for spellings ---

    first_name_just_updated = False
    last_name_just_updated = False

    if not conv.state.known_first_name:
        if not in_history("customer_first_name_spelling_asked"):
            conv.write_metric("FIRST_NAME_SPELLING_ASKED")
            return "Ask the user how to spell their first name."
        elif not is_na(conv, first_name):
            conv.state.first_name = first_name
            first_name_just_updated = True
    elif not is_na(conv, first_name):
        if not in_history("customer_first_name_spelling_confirmed"):
            conv.write_metric("FIRST_NAME_SPELLING_READ_BACK")
            spelling = name_to_spelling(conv.state.first_name)
            return (
                f"Read back the first name spelling to confirm it with the user. "
                f"The CORRECT spelling is exactly: {spelling}. You MUST use this spelling, "
                f"do NOT re-derive the spelling from the conversation transcript. "
                f"If the user says 'no', call this function again and set first_name='UNKNOWN'. "
                f"If the user provides a corrected spelling, call this function again with the corrected first_name. "
                f"If the user says 'yes', call 'customer_name_given' again with first_name='{conv.state.first_name}' and last_name set to whatever was provided. "
                f"If asked to repeat the spelling, always use the comma-separated format: {spelling}."
            )
        else:
            conv.state.first_name = first_name
            first_name_just_updated = True

    ack = (
        "Briefly acknowledge the spelling (e.g. 'Got it, thank you'). Then, "
        if first_name_just_updated
        else ""
    )

    if not last_name_refused and not conv.state.known_last_name:
        if not in_history("customer_last_name_spelling_asked"):
            conv.write_metric("LAST_NAME_SPELLING_ASKED")
            history = conv.state.get("values_in_history") or set()
            if "customer_first_name_spelling_asked" in history:
                return f"{ack}ask the user to spell their last name for you as well."
            else:
                return f"{ack}ask the user to spell their last name for you."
        elif not is_na(conv, last_name):
            conv.state.last_name = last_name
            last_name_just_updated = True
    elif not last_name_refused and not is_na(conv, last_name):
        if not in_history("customer_last_name_spelling_confirmed"):
            conv.write_metric("LAST_NAME_SPELLING_READ_BACK")
            spelling = name_to_spelling(conv.state.last_name)
            return (
                f"{ack}Read back the last name spelling to confirm it with the user. "
                f"The CORRECT spelling is exactly: {spelling}. You MUST use this spelling, "
                f"do NOT re-derive the spelling from the conversation transcript. "
                f"If the user provides a corrected spelling, call this function again with the corrected last_name. "
                f"If the user says 'no', call this function again and set last_name='UNKNOWN'. "
                f"If the user says 'yes', call 'customer_name_given' again with last_name='{conv.state.last_name}' and first_name set to whatever was provided. "
                f"If asked to repeat the spelling, always use the comma-separated format: {spelling}."
            )
        else:
            conv.state.last_name = last_name
            last_name_just_updated = True

    # --- 3) Second LLM extraction after spelling turns ---

    history = conv.state.get("values_in_history") or set()
    if (
        "customer_first_name_spelling_asked" in history
        or "customer_last_name_spelling_asked" in history
    ) and not in_history("customer_name_final_llm_extraction"):
        latest = (
            conv.state.customer_name_alternatives[-1]
            if conv.state.customer_name_alternatives
            else conv.state.customer_name_alternatives
        )
        (
            conv.state.first_name,
            conv.state.last_name,
            conv.state.known_first_name,
            conv.state.known_last_name,
        ) = extract_name(
            conv,
            latest,
            default_first_name=conv.state.get("first_name") or first_name
            if not is_na(conv, first_name)
            else "UNKNOWN",
            default_last_name=conv.state.get("last_name") or last_name
            if not is_na(conv, last_name)
            else "UNKNOWN",
        )
        if last_name_refused:
            conv.state.last_name = conv.state.first_name
            conv.state.known_last_name = conv.state.known_first_name

    # --- 4) Finalise and save ---

    first_name_processed = transform_name_spelling_string(conv.state.first_name)
    conv.state.first_name_spelling = first_name_processed.capitalize()
    conv.state.first_name_confirmed = True

    if last_name_refused:
        conv.state.last_name_spelling = conv.state.first_name_spelling
    else:
        last_name_processed = transform_name_spelling_string(conv.state.last_name)
        conv.state.last_name_spelling = last_name_processed.capitalize()
    conv.state.last_name_confirmed = True

    conv.write_metric("CREATE_BOOKING_FIRST_NAME_COLLECTED")
    conv.write_metric("CREATE_BOOKING_LAST_NAME_COLLECTED")
    conv.write_metric(
        "FIRST_NAME_CONFIDENCE", "HIGH" if conv.state.known_first_name else "LOW"
    )
    conv.write_metric(
        "LAST_NAME_CONFIDENCE", "HIGH" if conv.state.known_last_name else "LOW"
    )

    # --- Phone routing ---

    conv.log.info(
        "Customer name collected",
        first_name_spelling=conv.state.first_name_spelling,
        last_name_spelling=conv.state.last_name_spelling,
        known_first_name=conv.state.known_first_name,
        known_last_name=conv.state.known_last_name,
        last_name_refused=last_name_refused,
        phone_number=conv.caller_number,
        is_valid_mobile=is_valid_potential_mobile_number(conv, conv.caller_number),
    )

    extra_prompt_international_number = ""
    if conv.caller_number and is_valid_potential_mobile_number(
        conv, conv.caller_number
    ):
        conv.state.origin_step = "Should use callers phone number"
        flow.goto_step("Should use callers phone number")
    else:
        conv.state.origin_step = "Collect phone number"
        country_code = get_country_code(conv)
        local_prefix = {"GB": "+44", "IE": "+353"}.get(country_code, "NONE")
        if (
            conv.caller_number
            and conv.caller_number.startswith("+")
            and not conv.caller_number.startswith(local_prefix)
        ):
            extra_prompt_international_number = " When asking user for phone number, make sure to remind them to give you the number including the country code."
        flow.goto_step("Collect phone number")

    if last_name_refused:
        return f"Let the user know that not providing a surname is not a problem.{extra_prompt_international_number}"
    if last_name_just_updated:
        return f"Briefly acknowledge the spelling (e.g. 'Perfect, thank you').{extra_prompt_international_number}"
    return None
