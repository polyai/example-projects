from _gen import *  # <AUTO GENERATED>
import json
import logging


logger = logging.getLogger(__name__)

ORDER_NUMBER_NORMALIZATION_PROMPT = """
You are an extraction system for order numbers.

Call language context:
$language_context

Rules:
- A valid order number is: optional single letter prefix (P, U, or T) followed by 19 digits
- Keep only uppercase letters and digits in the final value
- Remove spaces, hyphens, periods, and punctuation
- Convert spoken digits to numerals:
  - English: zero=0, one=1, two=2, three=3, four=4, five=5, six=6, seven=7, eight=8, nine=9
  - French: zéro=0, un/une=1, deux=2, trois=3, quatre=4, cinq=5, six=6, sept=7, huit=8, neuf=9
- Convert "oh"/"o" to 0, "double X" to XX, "triple Y" to YYY
- If a letter prefix sounds like P/B/T/D, prefer P (most common for production orders)
- If no valid order number can be formed, return null

Output strictly JSON with this shape and no other text:
{"order_number": "<NORMALIZED_ORDER_NUMBER_OR_NULL>"}

Input text:
$raw_order_number
"""


def _get_language_context(conv: Conversation) -> str:
    lang = (getattr(conv.state, "language", "") or "").strip().lower()
    if lang == "fr-ca":
        return (
            "The caller is speaking French. Prioritize French spoken-number normalization "
            "(zéro, un, deux, trois, quatre, cinq, six, sept, huit, neuf)."
        )
    return "The conversation is in English or unspecified language."


def try_normalize_order_number(conv: Conversation, raw_order_number: str) -> str | None:
    if not raw_order_number:
        return None

    prompt = ORDER_NUMBER_NORMALIZATION_PROMPT.replace(
        "$language_context", _get_language_context(conv)
    ).replace("$raw_order_number", raw_order_number)

    try:
        result = conv.utils.prompt_llm(
            prompt=prompt, show_history=False, return_json=True
        )
        if isinstance(result, str):
            result = json.loads(result)

        candidate = result.get("order_number")
        if candidate and isinstance(candidate, str) and candidate != "null":
            normalized = "".join(ch for ch in candidate.upper() if ch.isalnum())
            return normalized
    except Exception as exc:
        logger.exception(f"Order number LLM normalization failed: {exc}")

    return None


@func_description(
    "LLM-based order number normalization for French/English spoken input."
)
def normalize_order_number(conv: Conversation, flow: Flow):
    pass
