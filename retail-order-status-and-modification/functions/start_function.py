from _gen import *  # <AUTO GENERATED>
import re


from .zendesk_client import search_user, search_user_phone

# Map the caller number to another number associated with an order for testing
SANDBOX_PHONE_NUMBER_MAPPING = {
    # "442045927510": "4163585075"
}

_LANGUAGE_MAP = {"French": "fr-CA", "English": "en-US"}


def _detect_language(conv: Conversation) -> str:
    rtc_lang = (conv.real_time_config.get("agent_initial_language", {}) or {}).get(
        "agent_initial_language", ""
    )
    lang_override = _LANGUAGE_MAP.get(rtc_lang, "")
    if lang_override == "fr-CA" and not conv.state.is_canada:
        conv.log.info(
            "Ignoring RTC French flag for non-Canada variant",
            rtc_language=rtc_lang,
            variant=conv.state.brand,
        )
        lang_override = ""
    if rtc_lang and not lang_override:
        conv.log.warning(
            "Unsupported RTC language; falling back to SIP/ASR",
            rtc_language=rtc_lang,
        )
    lang_header = conv.sip_headers.get("X-Language", "") or conv.sip_headers.get(
        "x-language", ""
    )
    raw_lang = lang_override or lang_header or conv.language or "en-US"
    if raw_lang.lower().startswith("fr") or (
        raw_lang in _LANGUAGE_MAP and _LANGUAGE_MAP[raw_lang] == "fr-CA"
    ):
        detected = "fr-CA"
    else:
        detected = "en-US"
    conv.log.info(
        "LANGUAGE",
        language=detected,
        source="rtc" if lang_override else ("sip_header" if lang_header else "asr"),
        raw=raw_lang,
    )
    return detected


def _digits_only(s: str) -> str:
    return re.sub(r"\D+", "", s or "")


def _is_phoney(s: str) -> bool:
    """
    Treat as phone-like if it contains 7–15 digits after stripping non-digits.
    This comfortably covers NANP and most E.164 cases without extra deps.
    """
    d = _digits_only(s)
    return 7 <= len(d) <= 15


def find_zendesk_user_by_email(conv: Conversation) -> bool:
    # Prefer email from Customer Core; fallback to SIP header email
    preferred_email = (conv.state.customer_email or conv.state.email or "").strip()
    if not preferred_email:
        conv.log.info(
            "find_zendesk_user_by_email: no email available (customer_core + SIP empty)"
        )
        return False

    try:
        res = search_user(conv, preferred_email)
    except Exception as e:
        conv.log.error(
            "Zendesk search_user (by email) failed",
            email_len=len(preferred_email),
            error=str(e),
        )
        return False

    count = int(res.get("count", 0) or 0)
    conv.log.info(
        "Zendesk user search by email",
        email_len=len(preferred_email),
        count=count,
        used_customer_core=bool(conv.state.customer_email),
    )

    if count > 0 and res.get("results"):
        user = res["results"][0]
        conv.state.zendesk_user_id = user["id"]

        zendesk_name = user.get("name") or ""
        first, last = split_full_name(zendesk_name)
        conv.state.zendesk_name = zendesk_name
        conv.state.zendesk_first_name = first
        conv.state.zendesk_last_name = last

        conv.log.info(
            "Zendesk user found by email",
            user_id=user["id"],
            used_customer_core=bool(conv.state.customer_email),
        )
        return True

    conv.log.info(
        "Zendesk user not found by email",
        email_len=len(preferred_email),
        used_customer_core=bool(conv.state.customer_email),
    )
    return False


def find_zendesk_user_by_phone(conv: Conversation) -> bool:
    raw = conv.state.phone_number or conv.caller_number or ""
    if not raw:
        conv.log.info("find_zendesk_user_by_phone: no phone number available on state")
        return False

    d = _digits_only(raw)

    attempts: list[tuple[str, str]] = []
    # 1) try current as-is first
    attempts.append((raw, "as-is"))

    # 2) if starts with '1' and is 11-digit -> try stripped
    if len(d) == 11 and d.startswith("1"):
        attempts.append((d[1:], "US-stripped"))
    # 3) else if 10-digit -> try with leading 1
    elif len(d) == 10:
        attempts.append(("1" + d, "US-prefixed"))

    seen = set()
    ordered_attempts = []
    for num, label in attempts:
        key = _digits_only(num)
        if key not in seen:
            seen.add(key)
            ordered_attempts.append((num, label))

    for number, label in ordered_attempts:
        try:
            res = search_user_phone(conv, number)
        except Exception as e:
            conv.log.error(
                "Zendesk search_user failed", attempt=label, number=number, error=str(e)
            )
            continue

        count = int(res.get("count", 0) or 0)
        conv.log.info(
            "Zendesk user search attempt", attempt=label, number=number, count=count
        )

        if count > 0 and res.get("results"):
            user = res["results"][0]
            conv.state.zendesk_user_id = user["id"]

            zendesk_phone = user.get("phone")
            print(zendesk_phone)

            zendesk_name = user.get("name") or ""
            first, last = split_full_name(zendesk_name)

            if first.strip().lower() == "caller" and _is_phoney(last):
                conv.log.info(
                    "Skipping Zendesk name save due to Caller+phone pattern",
                    first=first,
                    last=last,
                    user_id=user["id"],
                )
            else:
                conv.state.zendesk_name = zendesk_name
                conv.state.zendesk_first_name = first
                conv.state.zendesk_last_name = last

            conv.log.info("Zendesk user found", user_id=user["id"], attempt=label)
            return True

    conv.log.info(
        "Zendesk user not found after all attempts",
        attempts=[lbl for _, lbl in ordered_attempts],
    )
    return False


def split_full_name(full_name: str) -> tuple[str, str]:
    parts = full_name.strip().split()

    if not parts:
        return "", ""

    if len(parts) == 1:
        return parts[0], ""

    return parts[0], " ".join(parts[1:])


def cleanup_phone_number(number: str):
    number = number.replace("-", "")
    number = number.replace(" ", "")
    number = number.lstrip("+")
    return number


def start_function(conv: Conversation):
    ############ TEST FLAGS ############
    conv.state.USE_MOCK_API = conv.real_time_config.get("use_mock_api", True)
    ###################################

    conv.log.info("Start function called")

    conv.state.brand = conv.sip_headers.get("X-Brand")
    if not conv.state.brand:
        if conv.variant:
            conv.state.brand = conv.variant_name
        else:
            conv.state.brand = "Poly Store"
    conv.write_metric("BRAND", conv.state.brand)

    conv.state.is_canada = False

    conv.state.email = conv.sip_headers.get("X-Email")

    # set variants
    variant_map = {
        "Poly Store": "Poly Store",
    }
    if conv.state.brand in variant_map:
        conv.set_variant(variant_map[conv.state.brand])

    conv.state.center_status = conv.sip_headers.get("X-Hours")
    conv.write_metric("HOURS", conv.state.center_status)

    conv.state.instructions_for_descriptions = """
                                                *****IMPORTANT INSTRUCTIONS*******: \n

                                                Always pay VERY CAREFUL ATTENTION to the "Quantity" field of each item: How many are there?

                                                Mention the item you're talking about, but do so as succinctly as possible - e.g., say "Nike crew socks", not "Nike 6 Pack Dri-FIT Plus Crew Socks - Men's"; say "Jordan Air Jordan 4" not "Jordan Air Jordan 4 Retro Remastered - Boys' Grade School." \n

                                                If there are multiple of the same item, mention them together - e.g., "I see you have four pairs of Nike shorts, and a New Balance cap" - not "I see you have two pairs of Nike shorts, a New Balance cap, and another two pairs of Nike shorts."

                                                Remember, if you're talking about a pair of shoes, use the plural - "The Nike Air Max have shipped", not "The Nike Air Max has shipped".

                                                For shoes, ALWAYS mention the size (e.g., "the Nike Air Max in a size 9") and gender if there are multiple pairs of the same shoe (e.g., "the men's Nike Air Max in a size 8.5 and the women's in a size 9"). Shoe size is how customers identify their pair.

                                                For non-shoe items (clothing, accessories, etc.), don't mention the color (e.g., "black/white"), size (e.g., "L", "XS"), gender (e.g., "Men's"/"Women's"/"Boys'"/"Girls'"), or age group (e.g., "Grade School") UNLESS items share the same product name and differ only in those attributes, OR the user specifically asks you. \n
                                                If you do mention the color, and the color is listed as something like "Black/white", pronounce this as "black and white".

                                                NEVER pronounce any slashes ("/") or dashes ("-") that might be present in the product description. And NEVER, EVER, EVER try and give a tracking link verbally.  When listing the order items, do not list them in point form or structured form. Instead, say it naturally as if you were speaking to a friend on the phone."""

    mock_caller_number = conv.real_time_config.get("mock_caller_number")
    conv.state.phone_number = mock_caller_number

    if not mock_caller_number:
        if conv.env == "pre-release" or conv.env == "live":
            conv.state.phone_number = conv.caller_number

    if not conv.state.phone_number:
        conv.state.phone_number = conv.caller_number
    # if not conv.state.phone_number and conv.env == "pre-release": # remove after testing
    #   conv.state.phone_number = "7085895583"
    # conv.state.phone_number = "6505555555"

    #  for checking users number is ok to send an SMS to:
    if conv.state.phone_number:
        conv.state.caller_number_cleanedup = cleanup_phone_number(
            conv.state.phone_number
        )

    TESTING_ENV = ["sandbox", "draft", "pre-release"]

    if conv.env in TESTING_ENV:
        conv.state.Env = "pre-release"
    else:
        conv.state.Env = conv.env

    # LANGUAGE DETECTION
    detected_lang = _detect_language(conv)

    # French is only supported for the Canada variants
    if detected_lang == "fr-CA" and not conv.state.is_canada:
        conv.log.info(
            "French requested on non-Canada variant; overriding to English",
            variant=conv.state.brand,
        )
        detected_lang = "en-US"

    conv.set_language(detected_lang)
    conv.state.language = detected_lang
    conv.write_metric("LANGUAGE", detected_lang)

    # VOICE SET UP
    if detected_lang == "fr-CA":
        conv.set_voice(
            ElevenLabsVoice(
                provider_voice_id="IPgYtHTNLjC7Bq7IPHrm",
                similarity_boost=0.75,
                stability=1.0,
                model_id="eleven_turbo_v2_5",
            )
        )
    else:
        conv.set_voice(
            ElevenLabsVoice(
                provider_voice_id="vBKc2FfBKJfcZNyEt1n6",
                similarity_boost=0.75,
                stability=1.0,
                model_id="eleven_turbo_v2_5",
            )
        )

    conv.goto_flow("initial_ani_lookup")
    return {"utterance": "", "listen": {"asr": {"timeout": 0.1}}}
