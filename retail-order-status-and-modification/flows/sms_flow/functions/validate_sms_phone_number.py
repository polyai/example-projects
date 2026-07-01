from _gen import *  # <AUTO GENERATED>
from functions.utterances import utterance


def is_phone_number_valid(sms_phone_number: str):
    return len(sms_phone_number) == 10


def cleanup_phone_number(number: str):
    number = number.replace("-", "")
    number = number.replace(" ", "")
    number = number.replace(".", "")
    if number.startswith("+1"):
        number = number[2:]
    elif number.startswith("1") and len(number) == 11:
        number = number[1:]
    return "".join(char for char in number if char.isdigit())


def format_readback(digits: str) -> str:
    """3-3-4 grouping for spoken readback."""
    if len(digits) != 10:
        return " ".join(digits)
    return f"{digits[0:3]}... {digits[3:6]}... {digits[6:10]}"


@func_description("Validate the phone number provided by the user")
@func_parameter(
    "sms_phone_number",
    "The 10-digit phone number as a digit-only string. Convert spoken words to digits before passing: 'oh'/'O'/zéro = 0, 'double five' = 55, 'triple eight' = 888. French digits: cinq = 5, sept = 7, huit = 8, neuf = 9, quatre = 4, trois = 3, deux = 2, six = 6. French compound numbers: 'soixante-dix-huit' = 78, 'quatre-vingt-dix' = 90, 'sept cent quinze' = 715, 'trois cent deux' = 302. ASR misrecognitions: 'zet'/'set' = 7 (sept), 'sank'/'sunk' = 5 (cinq), 'weet'/'wheat' = 8 (huit), 'nuf' = 9 (neuf), 'twah' = 3 (trois). Strip spaces, dashes, punctuation, and filler words.",
)
def validate_sms_phone_number(conv: Conversation, flow: Flow, sms_phone_number: str):
    sms_phone_number = cleanup_phone_number(sms_phone_number)

    if is_phone_number_valid(sms_phone_number):
        conv.state.sms_phone_number_readback = format_readback(sms_phone_number)
        flow.goto_step("Read Back Number")
        return

    if not conv.state.sms_phone_number_validation_attempts:
        conv.state.sms_phone_number_validation_attempts = 0
    conv.state.sms_phone_number_validation_attempts += 1

    if conv.state.sms_phone_number_validation_attempts >= 2:
        conv.write_metric("SMS_FAILED")
        failed_step = (
            "WISMO check - sending failed" if conv.state.coming_from_WISMO else "SMS failed"
        )
        return {
            "utterance": utterance(conv, "sms_failed_text"),
            "transition": {"goto_flow": "SMS flow", "goto_step": failed_step},
        }

    # Offer DTMF on first failure
    return {
        "utterance": utterance(conv, "sms_phone_dtmf_fallback"),
        "transition": {
            "goto_flow": "SMS flow",
            "goto_step": "Phone number collected",
        },
    }
