import re

from _gen import *  # <AUTO GENERATED>
from flows.oms_idnv.functions.idnv_utils import (
    DIGIT_ASR_CORRECTIONS,
    LETTER_ASR_CORRECTIONS,
    ActionsIterator,
    get_bullet_points,
    invert_list_dict,
    try_alternative_postal_transcripts,
    try_alternative_transcripts,
)
from flows.oms_wismo.functions.determine_order_status import determine_order_status
from functions.step_utils import is_ca_from_state
from functions.utterances import utterance

SUPPORTED_COUNTRIES = {"US", "CA"}


def _get_candidates(conv) -> list:
    if getattr(conv.state, "order_from_full_order_number", None):
        return [conv.state.order_from_full_order_number]
    if getattr(conv.state, "orders_from_phone_number", None):
        return conv.state.orders_from_phone_number
    return []


# ---------------------------------------------------------------------------
# US zipcode helpers (5-digit numeric)
# ---------------------------------------------------------------------------


def _cleanup_zipcode(raw: str) -> str:
    raw = raw.replace("-", "").replace(" ", "").replace(".", "")
    digits = "".join(c for c in raw if c.isdigit())
    return digits[:5] if len(digits) == 9 else digits


def _is_valid_zipcode(code: str) -> bool:
    return len(code) == 5


def _try_zipcode_alternatives(conv) -> str | None:
    """Try ASR alternative transcripts to extract a valid 5-digit zipcode."""
    for alt in try_alternative_transcripts(conv, 5):
        cleaned = _cleanup_zipcode(alt)
        if _is_valid_zipcode(cleaned):
            conv.log.info("Trying alternative zipcode", zipcode=cleaned)
            return cleaned
    return None


def _handle_invalid_zipcode(conv):
    """Return retry actions when a US zipcode is invalid."""
    conv.write_metric("IDNV_ZIPCODE_INVALID")
    return ActionsIterator(
        "INVALID_BILLING_ZIPCODE_ACTIONS",
        [
            {
                "utterance": utterance(conv, "idnv_zip_invalid"),
                "content": get_bullet_points(
                    "If the user provides their zipcode-even if it's same as before-immediately call the function zipcode_provided."
                ),
            },
            {
                "utterance": utterance(conv, "idnv_zip_invalid_transfer"),
                "content": get_bullet_points(
                    "If the user says 'yes', immediately call transfer_call with handoff_reason = 'IDNV_FAILED' and handoff_utterance = 'DEFAULT'",
                    "If the user says 'no' or 'no, thanks', immediately says: 'Can I have your zipcode again?'.",
                ),
            },
        ],
    ).get_next(conv)


# ---------------------------------------------------------------------------
# CA postcode helpers (6-char alphanumeric A1A1A1)
# ---------------------------------------------------------------------------


def _cleanup_postcode(raw: str) -> str:
    text = raw
    for incorrect, correct in invert_list_dict(DIGIT_ASR_CORRECTIONS).items():
        text = re.sub(incorrect, correct, text, flags=re.IGNORECASE)
    for incorrect, correct in invert_list_dict(LETTER_ASR_CORRECTIONS).items():
        text = re.sub(incorrect, correct, text, flags=re.IGNORECASE)
    text = text.replace("-", "").replace(" ", "").replace(".", "")
    code = "".join(c for c in text if c.isalnum())
    return code.upper()


def _is_valid_postcode(code: str) -> bool:
    return bool(re.match(r"^[A-Z]\d[A-Z]\d[A-Z]\d$", code))


def _try_postcode_alternatives(conv) -> str | None:
    """Try ASR alternative transcripts to extract a valid CA postal code."""
    for alt in try_alternative_postal_transcripts(conv):
        cleaned = _cleanup_postcode(alt)
        if _is_valid_postcode(cleaned):
            conv.log.info("Trying alternative postal code", postal_code=cleaned)
            return cleaned
    return None


def _handle_invalid_postcode(conv):
    """Return retry actions when a CA postal code is invalid."""
    conv.write_metric("IDNV_ZIPCODE_INVALID")
    return ActionsIterator(
        "INVALID_BILLING_POSTAL_CODE_ACTIONS",
        [
            {
                "utterance": utterance(conv, "idnv_postal_invalid"),
                "content": get_bullet_points(
                    "If the user provides their postal code — even if it's the same as before — immediately call the function zipcode_provided."
                ),
            },
            {
                "utterance": utterance(conv, "idnv_postal_invalid_transfer"),
                "content": get_bullet_points(
                    "If the user says 'yes', immediately call transfer_call with handoff_reason = 'IDNV_FAILED' and handoff_utterance = 'DEFAULT'",
                    "If the user says 'no' or 'no, thanks', immediately says: 'Can I have your postal code again?'.",
                ),
            },
        ],
    ).get_next(conv)


# ---------------------------------------------------------------------------
# Shared: international order check
# ---------------------------------------------------------------------------


def _check_international_handoff(conv, candidates):
    """Hand off if any candidate order has a billing country outside US/CA."""
    if conv.real_time_config.get(
        "ignore_international_billing_zip_handoff_for_testing"
    ):
        return None
    international = next(
        (
            o
            for o in candidates
            if getattr(o, "billing_country_code", "US") not in SUPPORTED_COUNTRIES
        ),
        None,
    )
    if international:
        conv.write_metric("INTERNATIONAL_BILLING_ZIP")
        return conv.functions.transfer_call(
            "DEFAULT",
            "INTERNATIONAL_BILLING_ZIP",
            utterance(conv, "idnv_international_zip"),
        )
    return None


# ---------------------------------------------------------------------------
# Main entry point — called by both "Collect billing zipcode" and
# "Collect billing postcode" steps
# ---------------------------------------------------------------------------


@func_description(
    "Check the zipcode or postal code provided is correct. This function must be called every time the user provides any number or alphanumeric code."
)
@func_parameter(
    "billing_postal_code",
    "the billing zipcode or postal code provided by the user. Convert number words to digits (e.g. 'four' to '4') and letter words to letters (e.g. 'and' to 'N') before passing.",
)
def zipcode_provided(conv: Conversation, flow: Flow, billing_postal_code: str):
    is_ca = is_ca_from_state(conv)
    candidates = _get_candidates(conv)

    # International order check (applies to both US and CA)
    handoff = _check_international_handoff(conv, candidates)
    if handoff:
        return handoff

    # ---------- CA path: validate as 6-char postal code ----------
    if is_ca:
        conv.state.billing_postal_code = _cleanup_postcode(billing_postal_code)
        conv.log.info(
            "Collected postal code", postal_code=conv.state.billing_postal_code
        )

        if not _is_valid_postcode(conv.state.billing_postal_code):
            alt = _try_postcode_alternatives(conv)
            if alt:
                conv.state.billing_postal_code = alt
            else:
                return _handle_invalid_postcode(conv)

    # ---------- US path: validate as 5-digit zipcode ----------
    else:
        conv.state.billing_postal_code = _cleanup_zipcode(billing_postal_code)
        conv.log.info("Collected zipcode", zipcode=conv.state.billing_postal_code)

        if not _is_valid_zipcode(conv.state.billing_postal_code):
            alt = _try_zipcode_alternatives(conv)
            if alt:
                conv.state.billing_postal_code = alt
            else:
                return _handle_invalid_zipcode(conv)

    conv.write_metric("IDNV_ZIPCODE_COLLECTED", "True")
    return _save_and_match(conv, flow, is_ca)


# ---------------------------------------------------------------------------
# Shared: match collected code against candidate orders
# ---------------------------------------------------------------------------


def _normalize(code: str) -> str:
    return code.replace("-", "").replace(" ", "").upper()


def _save_and_match(conv, flow, is_ca: bool):
    """Try to match the collected code against candidate orders."""
    order_matched = None
    if conv.state.order_from_full_order_number:
        if (
            _normalize(conv.state.order_from_full_order_number.billing_postal_code)
            == conv.state.billing_postal_code
        ):
            order_matched = conv.state.order_from_full_order_number
    elif conv.state.orders_from_phone_number:
        order_matched = next(
            (
                o
                for o in conv.state.orders_from_phone_number
                if _normalize(o.billing_postal_code) == conv.state.billing_postal_code
            ),
            None,
        )
    else:
        conv.log.error("zipcode_provided called without candidate order(s)")

    # International check on matched/candidate orders
    if (
        order_matched
        and getattr(order_matched, "billing_country_code", "US")
        not in SUPPORTED_COUNTRIES
    ):
        conv.write_metric("INTERNATIONAL_BILLING_ZIP")
        return conv.functions.transfer_call(
            "DEFAULT",
            "INTERNATIONAL_BILLING_ZIP",
            utterance(conv, "idnv_international_zip"),
        )

    if not order_matched:
        candidates = _get_candidates(conv)
        if candidates and all(
            getattr(o, "billing_country_code", "US") not in SUPPORTED_COUNTRIES
            for o in candidates
        ):
            conv.write_metric("INTERNATIONAL_BILLING_ZIP")
            return conv.functions.transfer_call(
                "DEFAULT",
                "INTERNATIONAL_BILLING_ZIP",
                utterance(conv, "idnv_international_zip"),
            )

        # No match — ask user to retry
        if is_ca:
            flow.goto_step("Collect billing postcode")
            return ActionsIterator(
                "BILLING_POSTAL_CODE_NOT_FOUND_ACTION",
                [
                    {
                        "utterance": utterance(conv, "idnv_postal_mismatch"),
                        "content": get_bullet_points(
                            "If the user provides their postal code — even if it's the same as before — immediately call the function zipcode_provided",
                            "If the user says 'no', immediately call transfer_call with handoff_reason = 'IDNV_FAILED' and handoff_utterance = 'DEFAULT'",
                        ),
                    },
                    {
                        "utterance": utterance(conv, "idnv_still_no_match_transfer"),
                        "content": get_bullet_points(
                            "If the user provides their postal code — even if it's the same as before — immediately call the function zipcode_provided.",
                            "If the user says 'yes', immediately call transfer_call with handoff_reason = 'IDNV_FAILED' and handoff_utterance = 'DEFAULT'",
                            "If the user says 'no' or 'no, thanks', immediately says: 'Can I have your postal code again?'.",
                        ),
                    },
                ],
            ).get_next(conv)
        else:
            flow.goto_step("Collect billing zipcode")
            return ActionsIterator(
                "BILLING_ZIPCODE_NOT_FOUND_ACTION",
                [
                    {
                        "utterance": utterance(conv, "idnv_zip_mismatch"),
                        "content": get_bullet_points(
                            "If the user provides their zipcode — even if it's the same number as before — immediately call the function zipcode_provided",
                            "If the user says 'no', immediately call transfer_call with handoff_reason = 'IDNV_FAILED' and handoff_utterance = 'DEFAULT'",
                        ),
                    },
                    {
                        "utterance": utterance(conv, "idnv_still_no_match_transfer"),
                        "content": get_bullet_points(
                            "If the user provides their zipcode — even if it's the same number as before — immediately call the function zipcode_provided.",
                            "If the user says 'yes', immediately call transfer_call with handoff_reason = 'IDNV_FAILED' and handoff_utterance = 'DEFAULT'",
                            "If the user says 'no' or 'no, thanks', immediately says: 'Can I have your zipcode again?'.",
                        ),
                    },
                ],
            ).get_next(conv)

    # Match found
    conv.write_metric("IDNV_ZIPCODE_MATCHED")

    # Reset all counters
    for key in (
        "IDNV_ZIPCODE_INVALID",
        "BILLING_ZIPCODE_NOT_FOUND_ACTION",
        "INVALID_BILLING_ZIPCODE_ACTIONS",
        "BILLING_POSTAL_CODE_NOT_FOUND_ACTION",
        "INVALID_BILLING_POSTAL_CODE_ACTIONS",
    ):
        if hasattr(conv.state, key):
            setattr(conv.state, key, None)

    should_collect_last6 = (
        conv.state.using_phone_number and not conv.state.singleton_order
    )

    if should_collect_last6:
        flow.goto_step("Collect last 4")
        conv.say(utterance(conv, "idnv_collect_last4_with_hint"))
    else:
        conv.state.idnv_passed = True
        conv.write_metric("IDNV_SUCCESSFUL")
        conv.state.order_details = order_matched
        conv.state.transfer_on_silence_loop = False
        conv.state.in_idnv_flow = False
        conv.goto_flow("OMS_WISMO")
        return determine_order_status(conv, flow)
